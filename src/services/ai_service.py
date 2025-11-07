"""
AI Service for NetworkSwitch AI Assistant using LangChain
"""

import json
import re
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import asyncio

from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from core.config import AppConfig
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
    """AI Service for network switch assistance using LangChain"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger("ai_service")
        self.llm = None
        self.memory = None
        self.chains = {}
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize AI service with LangChain"""
        try:
            # Initialize Ollama LLM
            self.llm = Ollama(
                model=self.config.ai.model_name,
                base_url=self.config.ai.ollama_url,
                temperature=self.config.ai.temperature,
                top_p=self.config.ai.top_p,
                timeout=self.config.ai.timeout
            )
            
            # Test connection to Ollama
            await self._test_ollama_connection()
            
            # Initialize conversation memory
            self.memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                max_token_limit=4000
            )
            
            # Initialize specialized chains
            await self._initialize_chains()
            
            self.is_initialized = True
            self.logger.info(f"AI service initialized with model: {self.config.ai.model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AI service: {e}")
            return False
    
    async def _test_ollama_connection(self):
        """Test connection to Ollama service"""
        try:
            # Simple test query
            response = await asyncio.to_thread(
                self.llm.invoke,
                "Hello, this is a test. Please respond with 'AI service online'."
            )
            
            if "AI service online" in response:
                self.logger.info("Ollama connection test successful")
            else:
                self.logger.warning(f"Ollama connection test response: {response}")
                
        except Exception as e:
            self.logger.error(f"Ollama connection test failed: {e}")
            raise
    
    async def _initialize_chains(self):
        """Initialize specialized LangChain chains"""
        try:
            # General conversation chain
            general_prompt = PromptTemplate(
                template=AI_SYSTEM_PROMPTS[AIPromptType.GENERAL],
                input_variables=["question", "chat_history"]
            )
            
            self.chains["general"] = LLMChain(
                llm=self.llm,
                prompt=general_prompt,
                memory=self.memory,
                verbose=True
            )
            
            # Network troubleshooting chain
            troubleshooting_prompt = PromptTemplate(
                template=AI_SYSTEM_PROMPTS[AIPromptType.NETWORK_TROUBLESHOOTING],
                input_variables=["question", "context", "chat_history"]
            )
            
            self.chains["troubleshooting"] = LLMChain(
                llm=self.llm,
                prompt=troubleshooting_prompt,
                memory=self.memory,
                verbose=True
            )
            
            # Configuration assistance chain
            config_prompt = PromptTemplate(
                template=AI_SYSTEM_PROMPTS[AIPromptType.CONFIGURATION_ASSISTANCE],
                input_variables=["question", "vendor_type", "device_model", "chat_history"]
            )
            
            self.chains["configuration"] = LLMChain(
                llm=self.llm,
                prompt=config_prompt,
                memory=self.memory,
                verbose=True
            )
            
            # Command explanation chain
            explanation_prompt = PromptTemplate(
                template=AI_SYSTEM_PROMPTS[AIPromptType.COMMAND_EXPLANATION],
                input_variables=["command", "vendor_type", "context", "chat_history"]
            )
            
            self.chains["explanation"] = LLMChain(
                llm=self.llm,
                prompt=explanation_prompt,
                memory=self.memory,
                verbose=True
            )
            
            # Best practices chain
            best_practices_prompt = PromptTemplate(
                template=AI_SYSTEM_PROMPTS[AIPromptType.BEST_PRACTICES],
                input_variables=["topic", "vendor_type", "context", "chat_history"]
            )
            
            self.chains["best_practices"] = LLMChain(
                llm=self.llm,
                prompt=best_practices_prompt,
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
            AIPromptType.NETWORK_TROUBLESHOOTING: sum(1 for keyword in troubleshooting_keywords if keyword in query_lower),
            AIPromptType.CONFIGURATION_ASSISTANCE: sum(1 for keyword in config_keywords if keyword in config_keywords),
            AIPromptType.COMMAND_EXPLANATION: sum(1 for keyword in explanation_keywords if keyword in query_lower),
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
            "vendor_type": query.vendor_type or "unknown",
            "device_model": query.device_model or "unknown",
            "session_context": query.session_context or {},
            "command_history": query.command_history or [],
            "network_context": query.network_context or {}
        }
        
        # Add vendor-specific context if available
        if query.vendor_type and query.vendor_type in VENDOR_AI_PROMPTS:
            context["vendor_specific"] = VENDOR_AI_PROMPTS[query.vendor_type]
        
        return context
    
    async def process_query(self, query: AIQuery, streaming_callback=None) -> AIResponse:
        """Process AI query and return response"""
        if not self.is_initialized:
            return AIResponse(
                response="AI service is not initialized. Please check configuration.",
                confidence=0.0,
                query_type=AIPromptType.GENERAL,
                metadata={"error": "AI service not initialized"}
            )
        
        try:
            # Detect query type
            query_type = self._detect_query_type(query.query, query.context)
            
            # Prepare context
            context = self._prepare_context(query)
            
            # Get appropriate chain
            chain_name = query_type.value.lower().replace("_", "")
            chain = self.chains.get(chain_name, self.chains["general"])
            
            # Prepare input variables
            input_vars = {
                "question": query.query,
                "chat_history": self.memory.chat_memory.messages if self.memory else []
            }
            
            # Add context-specific variables
            if query_type == AIPromptType.NETWORK_TROUBLESHOOTING:
                input_vars["context"] = json.dumps(context, indent=2)
            elif query_type == AIPromptType.CONFIGURATION_ASSISTANCE:
                input_vars["vendor_type"] = context["vendor_type"]
                input_vars["device_model"] = context["device_model"]
            elif query_type == AIPromptType.COMMAND_EXPLANATION:
                input_vars["command"] = query.query
                input_vars["vendor_type"] = context["vendor_type"]
                input_vars["context"] = json.dumps(context, indent=2)
            elif query_type == AIPromptType.BEST_PRACTICES:
                input_vars["topic"] = query.query
                input_vars["vendor_type"] = context["vendor_type"]
                input_vars["context"] = json.dumps(context, indent=2)
            
            # Process query with streaming support
            if streaming_callback:
                # Create custom callback handler
                callback_handler = AIStreamingCallbackHandler(streaming_callback)
                
                # Process with streaming
                response = await asyncio.to_thread(
                    chain.run,
                    **input_vars,
                    callbacks=[callback_handler]
                )
            else:
                # Process without streaming
                response = await asyncio.to_thread(chain.run, **input_vars)
            
            # Calculate confidence based on response characteristics
            confidence = self._calculate_confidence(response, query_type, context)
            
            # Create AI response
            ai_response = AIResponse(
                response=response,
                confidence=confidence,
                query_type=query_type,
                metadata={
                    "model": self.config.ai.model_name,
                    "timestamp": datetime.utcnow().isoformat(),
                    "context": context,
                    "processing_time": 0  # Will be calculated by caller if needed
                }
            )
            
            self.logger.info(f"AI query processed successfully. Type: {query_type.value}, Confidence: {confidence:.2f}")
            return ai_response
            
        except Exception as e:
            self.logger.error(f"Failed to process AI query: {e}")
            return AIResponse(
                response="I apologize, but I encountered an error processing your request. Please try again.",
                confidence=0.0,
                query_type=query_type if 'query_type' in locals() else AIPromptType.GENERAL,
                metadata={"error": str(e)}
            )
    
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
    
    async def get_memory_summary(self) -> Dict[str, Any]:
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