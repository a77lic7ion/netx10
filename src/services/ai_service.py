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
from core.constants import AIPromptType, VENDOR_AI_PROMPTS, AI_SYSTEM_PROMPTS
from models.device_models import AIQuery, AIResponse
from utils.logging import get_logger


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
        self.is_initialized = False
        self._is_processing = False

    def is_processing(self) -> bool:
        """Check if the AI service is currently processing a query."""
        return self._is_processing
        
    async def initialize(self) -> bool:
        """Initialize AI service with LangChain"""
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
            
            self.is_initialized = True
            self.logger.info(f"AI service initialized with model: {self.ai_config.model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI service: {e}")
            return False
    
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
                prompt_text = f"{system_prompt}\n\nUser: {query.query}\n"
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
