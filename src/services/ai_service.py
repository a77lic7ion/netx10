"""
AI Service for NetworkSwitch AI Assistant using LangChain
"""

import json
import re
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import asyncio

try:
    from langchain_community.llms import Ollama
    from langchain.prompts import PromptTemplate
    from langchain.chains import LLMChain, ConversationalRetrievalChain
    from langchain.memory import ConversationBufferMemory
    from langchain.schema import BaseMessage, HumanMessage, AIMessage
    from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
    from langchain_openai import ChatOpenAI
    # Optional providers (loaded if installed)
    try:
        from langchain_anthropic import ChatAnthropic  # type: ignore
    except Exception:
        ChatAnthropic = None  # type: ignore
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
    except Exception:
        ChatGoogleGenerativeAI = None  # type: ignore

    _HAS_LANGCHAIN = True
except Exception:
    # LangChain / Ollama not available in test environments — provide fallbacks
    _HAS_LANGCHAIN = False

    class StreamingStdOutCallbackHandler:
        def __init__(self, *args, **kwargs):
            pass

    class PromptTemplate:
        def __init__(self, template: str, input_variables: list):
            self.template = template
            self.input_variables = input_variables

    # Minimal mock LLM used when Ollama isn't installed
    class _MockLLM:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def invoke(self, prompt: str) -> str:
            # Very small deterministic response for tests / offline use
            return f"[mock-llm] Received prompt: {prompt[:200]}"

from core.config import AppConfig, AIConfig, ProviderConfig
from core.constants import AIPromptType, VENDOR_AI_PROMPTS, AI_SYSTEM_PROMPTS, CROSS_VENDOR_MAPPINGS, VendorType
from models.device_models import AIQuery, AIResponse
from utils.logging_utils import get_logger


class AIStreamingCallbackHandler(StreamingStdOutCallbackHandler):
    """Custom streaming callback handler for AI responses"""
    
    def __init__(self, callback_func=None):
        super().__init__()
        self.callback_func = callback_func
        self.tokens = []
    
    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Handle new token from LLM"""
        self.tokens.append(token)
        if self.callback_func:
            self.callback_func(token)
    
    def get_full_response(self) -> str:
        """Get the complete response"""
        return "".join(self.tokens)


class AIService:
    """AI Service for network switch assistance using LangChain (or a mock fallback)."""

    def __init__(self, ai_config: AIConfig):
        # ai_config is expected to be AppConfig.ai (AIConfig) or similar
        self.ai_config = ai_config
        self.logger = get_logger("ai_service")
        self.llm = None
        self.memory = None
        # chains: str -> callable or chain object
        self.chains = {}
        self._initialized = False
        self._is_processing = False
        # Fallback text history when LangChain memory is unavailable
        self._text_history: List[Dict[str, str]] = []

    def is_initialized(self) -> bool:
        """Check if the AI service is initialized."""
        return self._initialized

    def is_processing(self) -> bool:
        """Check if the AI service is currently processing a query."""
        return self._is_processing
        
    async def initialize(self) -> bool:
        """Initialize AI service with LangChain"""
        self._is_processing = True
        self._initialized = False
        try:
            # Initialize LLM (Ollama if available, otherwise mock)
            if _HAS_LANGCHAIN:
                provider_name = self.ai_config.default_provider
                provider_config = self.ai_config.providers.get(provider_name)

                if not provider_config:
                    raise ValueError(f"Provider '{provider_name}' not configured.")

                self.llm = self._create_llm_instance(provider_name, provider_config)

                # Test connection to the selected provider
                await self._test_connection(provider_name)

                # Initialize conversation memory
                self.memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True,
                    max_token_limit=4000
                )

                # Initialize specialized chains
                await self._initialize_chains()
            else:
                # Fallback mock LLM for offline/testing
                self.llm = _MockLLM(model=self.ai_config.model_name)
                self.memory = None
                # No chains available; processing will call llm.invoke directly
            
            self._initialized = True
            self.logger.info(f"AI service initialized with model: {self.ai_config.model_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI service: {e}")
            self._initialized = False
        finally:
            self._is_processing = False
        
        return self._initialized
    
    def _create_llm_instance(self, provider_name: str, config: ProviderConfig) -> Any:
        """Factory function to create an LLM instance based on provider"""
        # Prefer provider-specific model override if present
        model_name = config.model or self.ai_config.model_name
        if provider_name == "ollama":
            return Ollama(
                model=model_name,
                base_url=str(config.base_url) if config.base_url else None,
                temperature=self.ai_config.temperature,
                top_p=self.ai_config.top_p,
                timeout=config.timeout
            )
        elif provider_name == "openai":
            return ChatOpenAI(
                model_name=model_name,
                openai_api_key=config.api_key,
                openai_api_base=str(config.base_url) if config.base_url else None,
                temperature=self.ai_config.temperature,
                max_tokens=self.ai_config.max_tokens,
                top_p=self.ai_config.top_p,
                timeout=config.timeout
            )
        elif provider_name == "xai":
            # xAI exposes an OpenAI-compatible API
            return ChatOpenAI(
                model_name=model_name,
                openai_api_key=config.api_key,
                openai_api_base=str(config.base_url) if config.base_url else "https://api.x.ai/v1",
                temperature=self.ai_config.temperature,
                max_tokens=self.ai_config.max_tokens,
                top_p=self.ai_config.top_p,
                timeout=config.timeout
            )
        elif provider_name == "mistral":
            # Mistral provides an OpenAI-compatible endpoint as well
            return ChatOpenAI(
                model_name=model_name,
                openai_api_key=config.api_key,
                openai_api_base=str(config.base_url) if config.base_url else "https://api.mistral.ai/v1",
                temperature=self.ai_config.temperature,
                max_tokens=self.ai_config.max_tokens,
                top_p=self.ai_config.top_p,
                timeout=config.timeout
            )
        elif provider_name == "anthropic":
            if ChatAnthropic is None:
                raise ValueError("Anthropic provider requested but langchain-anthropic is not installed.")
            return ChatAnthropic(
                model=model_name,
                api_key=config.api_key,
                temperature=self.ai_config.temperature,
                max_tokens=self.ai_config.max_tokens
            )
        elif provider_name == "gemini":
            if ChatGoogleGenerativeAI is None:
                raise ValueError("Gemini provider requested but langchain-google-genai is not installed.")
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=config.api_key,
                temperature=self.ai_config.temperature,
                max_output_tokens=self.ai_config.max_tokens,
            )
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")
    
    async def _test_connection(self, provider_name: str):
        """Test connection to the selected AI service"""
        try:
            # Simple test query
            response = await asyncio.to_thread(
                self.llm.invoke,
                "Hello, this is a test. Please respond with 'AI service online'."
            )
            
            response_content = response if isinstance(response, str) else response.content

            if "AI service online" in response_content:
                self.logger.info(f"{provider_name.capitalize()} connection test successful")
            else:
                self.logger.warning(f"{provider_name.capitalize()} connection test response: {response_content}")
                
        except Exception as e:
            self.logger.error(f"{provider_name.capitalize()} connection test failed: {e}")
            raise
    
    async def _initialize_chains(self):
        """Initialize specialized LangChain chains"""
        try:
            # Initialize chain wrappers (only meaningful if langchain is available)
            # Map chain names to the AIPromptType keys used in AI_SYSTEM_PROMPTS
            mapping = {
                "general": AIPromptType.GENERAL,
                "troubleshooting": AIPromptType.TROUBLESHOOTING,
                "configuration": AIPromptType.CONFIG_TRANSLATION,
                "explanation": AIPromptType.EXPLANATION,
                "best_practices": AIPromptType.BEST_PRACTICES,
            }

            if _HAS_LANGCHAIN:
                for name, prompt_type in mapping.items():
                    prompt = PromptTemplate(
                        template=AI_SYSTEM_PROMPTS[prompt_type],
                        input_variables=["question", "chat_history"]
                    )

                    self.chains[name] = LLMChain(
                        llm=self.llm,
                        prompt=prompt,
                        memory=self.memory,
                        verbose=True
                    )
            
            self.logger.info("AI chains initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI chains: {e}")
            raise

    def map_query_to_vendor_command(self, query: str, vendor_type: str) -> Optional[str]:
        """Map a natural-language query to a vendor-specific CLI command.

        Supports common intents like viewing running configuration, interfaces, VLANs, version, and routing.
        Returns the single best-fit command for the given vendor or None if no match.
        """
        q = query.lower()

        # Intent detection via keyword patterns
        intent_patterns = {
            "show_running_config": [
                r"running\s*config",
                r"current\s*configuration",
                r"see\s*(the\s*)?config",
                r"show\s*(the\s*)?config",
                r"view\s*(the\s*)?config",
            ],
            "show_interfaces": [
                r"interfaces?\b",
                r"ports?\b",
                r"link\s*status",
                r"interface\s*status",
            ],
            "show_vlan": [
                r"vlan[s]?\b",
                r"switching\s*vlans",
                r"vlan\s*table",
            ],
            "show_version": [
                r"version\b",
                r"os\s*version",
                r"software\s*version",
                r"platform\s*info",
            ],
            "show_routing": [
                r"routing\b",
                r"route\b",
                r"routing\s*table",
            ],
        }

        matched_intent: Optional[str] = None
        for intent, patterns in intent_patterns.items():
            if any(re.search(p, q) for p in patterns):
                matched_intent = intent
                break

        if not matched_intent:
            return None

        # Resolve vendor enum
        try:
            vendor_enum = VendorType(vendor_type)
        except Exception:
            return None

        mapping = CROSS_VENDOR_MAPPINGS.get(matched_intent)
        if not mapping:
            return None
        return mapping.get(vendor_enum)

    def map_config_intent_to_vendor_commands(self, query: str, vendor_type: str) -> Optional[Dict[str, Any]]:
        """Detect simple configuration intents and return vendor-aware command sequences.

        Currently supports VLAN creation like:
        - "create vlan 70 named AP"
        - "make a vlan 70 and call it AP"
        - "add vlan id 70 name AP"

        Returns a dict with keys: {"commands": List[str], "summary": str}
        or None if no supported intent detected.
        """
        q = query.lower()

        # Detect VLAN creation intent
        vlan_intent_patterns = [
            r"\b(create|make|add)\b.*\bvlan\b",
            r"\bvlan\b.*\b(create|make|add)\b",
        ]
        if not any(re.search(p, q) for p in vlan_intent_patterns):
            # Also match bare phrases like "vlan 70 name AP"
            if not re.search(r"\bvlan\s*\d{1,4}\b", q):
                return None

        # Extract VLAN ID
        vid_match = (
            re.search(r"\bvlan\s*(?:id\s*)?(\d{1,4})", q)
            or re.search(r"\b(\d{1,4})\b.*\bvlan\b", q)
        )
        if not vid_match:
            return None
        try:
            vlan_id = int(vid_match.group(1))
        except Exception:
            return None

        # Extract VLAN name (optional)
        name_match = (
            re.search(r"\b(name|named|call\s*it|label)\s*[\'\"]?([A-Za-z0-9_\-]+)[\'\"]?", q)
        )
        vlan_name = name_match.group(2) if name_match else None

        # Resolve vendor enum
        try:
            vendor_enum = VendorType(vendor_type)
        except Exception:
            return None

        # Build vendor-aware commands
        commands: List[str] = []
        summary_parts: List[str] = []
        display_vendor = vendor_enum.name

        if vendor_enum == VendorType.CISCO:
            commands.extend([
                "configure terminal",
                f"vlan {vlan_id}",
            ])
            if vlan_name:
                commands.append(f"name {vlan_name}")
            commands.append("exit")
            summary_parts.append("Cisco IOS: conf t → vlan → name → exit")
        elif vendor_enum in (VendorType.H3C, VendorType.HUAWEI):
            commands.extend([
                "system-view",
                f"vlan {vlan_id}",
            ])
            if vlan_name:
                commands.append(f"description {vlan_name}")
            commands.append("quit")
            summary_parts.append("Comware/VRP: system-view → vlan → description → quit")
        elif vendor_enum == VendorType.JUNIPER:
            commands.extend([
                "configure",
                f"set vlans {vlan_name or f'VLAN{vlan_id}'} vlan-id {vlan_id}",
                "commit",
                "exit",
            ])
            summary_parts.append("JunOS: configure → set vlans → commit → exit")
        else:
            return None

        # Suggest a verification command at the end
        verify_cmd = {
            VendorType.CISCO: "show vlan",
            VendorType.H3C: "display vlan",
            VendorType.HUAWEI: "display vlan",
            VendorType.JUNIPER: "show vlans",
        }.get(vendor_enum)
        if verify_cmd:
            commands.append(verify_cmd)

        summary = (
            f"Create VLAN {vlan_id}"
            + (f" named {vlan_name}" if vlan_name else "")
            + f" on {display_vendor}."
        )
        if summary_parts:
            summary += " " + summary_parts[0]

        return {"commands": commands, "summary": summary}
    
    def _detect_query_type(self, query: str, context: Optional[Dict[str, Any]] = None) -> AIPromptType:
        """Detect the type of query based on content"""
        query_lower = query.lower()
        
        # Troubleshooting keywords
        troubleshooting_keywords = [
            "troubleshoot", "problem", "issue", "error", "not working", "failed",
            "down", "disconnected", "timeout", "packet loss", "latency"
        ]
        
        # Configuration keywords
        config_keywords = [
            "configure", "config", "setup", "enable", "disable", "vlan", "interface",
            "routing", "access list", "acl", "qos", "ospf", "bgp", "eigrp"
        ]
        
        # Command explanation keywords
        explanation_keywords = [
            "explain", "what does", "how does", "meaning", "purpose", "function"
        ]
        
        # Best practices keywords
        best_practices_keywords = [
            "best practice", "recommend", "should", "optimal", "standard", "guideline"
        ]
        
        # Score each category
        scores = {
            AIPromptType.TROUBLESHOOTING: sum(1 for keyword in troubleshooting_keywords if keyword in query_lower),
            AIPromptType.CONFIG_TRANSLATION: sum(1 for keyword in config_keywords if keyword in query_lower),
            AIPromptType.EXPLANATION: sum(1 for keyword in explanation_keywords if keyword in query_lower),
            AIPromptType.BEST_PRACTICES: sum(1 for keyword in best_practices_keywords if keyword in query_lower),
            AIPromptType.GENERAL: 0
        }
        
        # Return the category with highest score, default to GENERAL
        detected_type = max(scores, key=scores.get)
        
        # Override with explicit context if provided
        if context and "query_type" in context:
            try:
                return AIPromptType(context["query_type"])
            except ValueError:
                pass
        
        return detected_type
    
    def _prepare_context(self, query: AIQuery) -> Dict[str, Any]:
        """Prepare context for AI processing"""
        context = {
            "vendor_type": getattr(query, "vendor_type", "unknown"),
            "device_model": getattr(query, "device_model", "unknown"),
            "session_context": getattr(query, "session_context", {}) or {},
            "command_history": getattr(query, "command_history", []) or [],
            "network_context": getattr(query, "network_context", {}) or {}
        }
        
        # Add vendor-specific context if available
        if getattr(query, "vendor_type", None) and getattr(query, "vendor_type", None) in VENDOR_AI_PROMPTS:
            context["vendor_specific"] = VENDOR_AI_PROMPTS[getattr(query, "vendor_type")]
        
        return context
    
    async def process_query(self, query: AIQuery, streaming_callback=None) -> AIResponse:
        """Process AI query and return response"""
        if not self.is_initialized:
            return AIResponse(response="AI service is not initialized. Please check configuration.", confidence=0.0)
        
        self._is_processing = True
        try:
            # Detect query type
            query_type = self._detect_query_type(query.query, getattr(query, 'context', None))

            # Prepare context
            context = self._prepare_context(query)

            # Get appropriate chain name
            if query_type == AIPromptType.TROUBLESHOOTING:
                chain_name = "troubleshooting"
            elif query_type == AIPromptType.CONFIG_TRANSLATION:
                chain_name = "configuration"
            elif query_type == AIPromptType.EXPLANATION:
                chain_name = "explanation"
            elif query_type == AIPromptType.BEST_PRACTICES:
                chain_name = "best_practices"
            else:
                chain_name = "general"

            chain = self.chains.get(chain_name)

            # If langchain unavailable, fall back to direct invoke on llm
            if not _HAS_LANGCHAIN or chain is None:
                system_prompt = AI_SYSTEM_PROMPTS.get(query_type, "")
                # Include simple text history when LangChain memory isn't available
                history_text = ""
                if self._text_history:
                    recent = self._text_history[-8:]
                    formatted = "\n".join([f"{m['role'].capitalize()}: {m['text']}" for m in recent])
                    history_text = f"\nConversation context:\n{formatted}\n"
                prompt_text = f"{system_prompt}{history_text}\n\nUser: {query.query}\n"
                response = await asyncio.to_thread(self.llm.invoke, prompt_text)
            else:
                input_vars = {
                    "question": query.query,
                    "chat_history": self.memory.chat_memory.messages if self.memory else []
                }

                if streaming_callback:
                    callback_handler = AIStreamingCallbackHandler(streaming_callback)
                    response = await asyncio.to_thread(chain.run, **input_vars, callbacks=[callback_handler])
                else:
                    response = await asyncio.to_thread(chain.run, **input_vars)
            
            # Calculate confidence based on response characteristics
            confidence = self._calculate_confidence(response, query_type, context)

            # Create AI response (match models.device_models.AIResponse fields)
            ai_response = AIResponse(
                response=response,
                confidence=confidence
            )

            # Update fallback text history if LangChain memory is unavailable
            if not _HAS_LANGCHAIN:
                self._text_history.append({"role": "user", "text": query.query})
                self._text_history.append({"role": "ai", "text": response})

            self.logger.info(f"AI query processed successfully. Type: {query_type.value}, Confidence: {confidence:.2f}")
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Failed to process AI query: {e}")
            return AIResponse(response="I apologize, but I encountered an error processing your request. Please try again.", confidence=0.0)
        finally:
            self._is_processing = False
    
    def _calculate_confidence(self, response: str, query_type: AIPromptType, context: Dict[str, Any]) -> float:
        """Calculate confidence score for AI response"""
        confidence = 0.7  # Base confidence
        
        # Check for specific indicators of confidence
        response_lower = response.lower()
        
        # Positive indicators
        positive_indicators = [
            "based on", "according to", "typically", "usually", "recommended",
            "best practice", "standard", "common", "following", "steps"
        ]
        
        negative_indicators = [
            "i'm not sure", "i don't know", "unclear", "ambiguous",
            "insufficient information", "cannot determine", "unknown"
        ]
        
        # Count positive indicators
        positive_count = sum(1 for indicator in positive_indicators if indicator in response_lower)
        confidence += min(positive_count * 0.05, 0.2)  # Cap at 0.2
        
        # Count negative indicators
        negative_count = sum(1 for indicator in negative_indicators if indicator in response_lower)
        confidence -= min(negative_count * 0.1, 0.3)  # Cap at 0.3
        
        # Check for specific technical content
        if any(term in response_lower for term in ["interface", "vlan", "routing", "configuration"]):
            confidence += 0.05
        
        # Check for code/commands
        if any(marker in response for marker in ["show ", "config", "interface ", "vlan "]):
            confidence += 0.05
        
        # Ensure confidence is within bounds
        return max(0.0, min(1.0, confidence))
    
    async def generate_command_suggestions(self, vendor_type: str, context: Dict[str, Any]) -> List[str]:
        """Generate command suggestions based on context"""
        try:
            prompt = f"""
            Generate a list of useful network commands for {vendor_type} devices based on the following context:
            Context: {json.dumps(context, indent=2)}
            
            Please provide 5-10 commonly used commands that would be helpful in this situation.
            Format each command on a new line, without explanations.
            """
            
            response = await asyncio.to_thread(self.llm.invoke, prompt)
            
            # Parse commands from response
            commands = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and len(line) < 200:
                    commands.append(line)
            
            return commands[:10]  # Limit to 10 suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to generate command suggestions: {e}")
            return []
    
    async def analyze_network_issue(self, symptoms: List[str], device_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze network issues and provide recommendations"""
        try:
            prompt = f"""
            Analyze the following network issue symptoms and provide troubleshooting recommendations:
            
            Symptoms: {json.dumps(symptoms, indent=2)}
            Device Information: {json.dumps(device_info, indent=2)}
            
            Please provide:
            1. Most likely causes (2-3)
            2. Recommended diagnostic commands
            3. Step-by-step troubleshooting approach
            4. Prevention recommendations
            
            Format the response as JSON with clear sections.
            """
            
            response = await asyncio.to_thread(self.llm.invoke, prompt)
            
            # Try to parse JSON response
            try:
                analysis = json.loads(response)
            except json.JSONDecodeError:
                # Fallback to text parsing
                analysis = {
                    "likely_causes": self._extract_section(response, "causes", 3),
                    "diagnostic_commands": self._extract_section(response, "commands", 5),
                    "troubleshooting_steps": self._extract_section(response, "steps", 5),
                    "prevention": self._extract_section(response, "prevention", 3)
                }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze network issue: {e}")
            return {"error": str(e)}
    
    def _extract_section(self, text: str, section_name: str, max_items: int) -> List[str]:
        """Extract items from a section of text"""
        items = []
        lines = text.split('\n')
        in_section = False
        
        for line in lines:
            line_lower = line.lower()
            
            # Look for section start
            if section_name in line_lower and any(marker in line_lower for marker in [":", "-", "*"]):
                in_section = True
                continue
            
            # Extract items when in section
            if in_section:
                # Look for numbered or bulleted items
                if re.match(r'^[\s]*[\d\*\-\.]+[\s]+(.+)', line):
                    item = re.sub(r'^[\s]*[\d\*\-\.]+[\s]+', '', line).strip()
                    if item and len(item) > 5:
                        items.append(item)
                        if len(items) >= max_items:
                            break
                # Look for lines starting with common markers
                elif line.strip().startswith(('- ', '* ', '• ')):
                    item = line.strip()[2:].strip()
                    if item and len(item) > 5:
                        items.append(item)
                        if len(items) >= max_items:
                            break
        
        return items[:max_items]
    
    async def clear_memory(self):
        """Clear conversation memory"""
        try:
            if self.memory:
                self.memory.clear()
                self.logger.info("AI conversation memory cleared")
            # Fallback text history
            self._text_history.clear()
        except Exception as e:
            self.logger.error(f"Failed to clear AI memory: {e}")

    def clear_conversation_memory(self) -> None:
        """Synchronous wrapper to clear conversation memory.

        Some callers operate in sync context (e.g., session load) and cannot await.
        """
        try:
            if self.memory:
                self.memory.clear()
                self.logger.info("AI conversation memory cleared (sync)")
            self._text_history.clear()
        except Exception as e:
            self.logger.error(f"Failed to clear AI memory (sync): {e}")
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of conversation memory"""
        try:
            if not self.memory:
                return {"message_count": 0, "messages": []}
            
            messages = self.memory.chat_memory.messages
            return {
                "message_count": len(messages),
                "messages": [
                    {
                        "type": type(msg).__name__,
                        "content": msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    }
                    for msg in messages[-10:]  # Last 10 messages
                ]
            }
        except Exception as e:
            self.logger.error(f"Failed to get memory summary: {e}")
            return {"error": str(e)}

    def load_memory_summary(self, summary: Dict[str, Any]) -> None:
        """Load conversation memory from a saved summary.

        Expects the format returned by get_memory_summary(). Restores messages
        into LangChain memory if available; otherwise, populates fallback text history.
        """
        try:
            messages = summary.get("messages", []) if isinstance(summary, dict) else []
            if _HAS_LANGCHAIN and self.memory:
                # Clear current memory
                self.memory.clear()
                # Reconstruct messages
                for m in messages:
                    mtype = m.get("type", "HumanMessage")
                    content = m.get("content", "")
                    if not content:
                        continue
                    if mtype == "HumanMessage":
                        self.memory.chat_memory.add_message(HumanMessage(content=content))
                    elif mtype == "AIMessage":
                        self.memory.chat_memory.add_message(AIMessage(content=content))
                    else:
                        # Default to HumanMessage for unknown types
                        self.memory.chat_memory.add_message(HumanMessage(content=content))
                self.logger.info("AI conversation memory loaded into LangChain memory")
            else:
                # Fallback: basic text history
                self._text_history.clear()
                for m in messages:
                    content = m.get("content", "")
                    if not content:
                        continue
                    role = "ai" if m.get("type") == "AIMessage" else "user"
                    self._text_history.append({"role": role, "text": content})
                self.logger.info("AI conversation memory loaded into fallback history")
        except Exception as e:
            self.logger.error(f"Failed to load AI memory summary: {e}")

    async def close(self):
        """Close AI service"""
        try:
            # Clear memory
            await self.clear_memory()
            
            # Clear chains
            self.chains.clear()
            
            self.is_initialized = False
            self.logger.info("AI service closed")
            
        except Exception as e:
            self.logger.error(f"Error closing AI service: {e}")
