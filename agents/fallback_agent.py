#!/usr/bin/env python3
"""
Fallback Agent
Simplified agent without loops or tools, uses only RAG knowledge
"""

import json
import os
import time
from typing import List, Dict, Any, Optional

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from agents.base_agent import Agent, AgentContext, AgentResult

class FallbackAgent(Agent):
    """Simplified fallback agent using only RAG knowledge"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize OpenAI client if available
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key and api_key != 'your_openai_api_key_here':
                self.openai_client = openai.OpenAI(api_key=api_key)
                self.openai_enabled = True
            else:
                self.openai_client = None
                self.openai_enabled = False
        else:
            self.openai_client = None
            self.openai_enabled = False
    
    def get_system_prompt(self, context: AgentContext) -> str:
        """Simple system prompt for fallback"""
        return self.build_prompt(
            'CHARACTER_BASE_T3RN',
            'GAME_CONTEXT', 
            'CONTENT_RESTRICTIONS'
        )

    
    def call_llm(self, messages: List[Dict[str, Any]], channel_logger) -> Any:
        """Simple LLM call without tools"""
        
        if not self.openai_enabled:
            raise Exception("OpenAI not available for FallbackAgent")
        
        try:
            start_time = time.time()
            
            response = self.openai_client.chat.completions.create(
                model='gpt-4.1-mini',
                messages=messages,
                temperature=0.5,
                max_tokens=1000
            )
            
            elapsed_time = time.time() - start_time
            
            # Log call info
            prompt_tokens = response.usage.prompt_tokens if response.usage else 0
            completion_tokens = response.usage.completion_tokens if response.usage else 0
            total_tokens = response.usage.total_tokens if response.usage else 0
            
            channel_logger.log_to_logs(f"⚡ FallbackAgent completed in {elapsed_time:.3f}s ({prompt_tokens}+{completion_tokens}={total_tokens} tokens)")
            
            return response
            
        except Exception as e:
            channel_logger.log_to_logs(f"❌ FallbackAgent LLM error: {str(e)}")
            raise
    
    def execute(self, context: AgentContext, channel_logger) -> AgentResult:
        """Execute FallbackAgent with RAG knowledge only"""
        
        channel_logger.log_to_logs("🛡️ FallbackAgent starting with RAG knowledge")
        
        try:
            # Get original query
            original_query = context.original_user_message or "general help"
            
            # Pre-load RAG data
            from tools_rag.rag_get_general_knowledge import rag_get_general_knowledge
            general_knowledge = rag_get_general_knowledge(original_query)
            channel_logger.log_to_logs(f"🔍 FallbackAgent pre-loaded RAG data for: {original_query}")
            
            # Prepare simple messages
            messages = [{
                "role": "system",
                "content": self.get_system_prompt(context)
            }]
            
            # Add RAG context if available
            if general_knowledge:
                messages.append({
                    "role": "system", 
                    "content": f"Available knowledge: {general_knowledge}"
                })
            
            # Add user question
            messages.append({
                "role": "user",
                "content": original_query
            })
            
            # Call LLM (no tools)
            channel_logger.log_to_logs("🤖 FallbackAgent calling ChatGPT-4o-mini without tools")
            response = self.call_llm(messages, channel_logger)
            
            # Get response
            response_content = response.choices[0].message.content or "No response generated"
            
            channel_logger.log_to_logs("✅ FallbackAgent completed successfully")
            
            result = AgentResult()
            result.final_answer = response_content
            result.error_content = ""
            
            return result
            
        except Exception as e:
            channel_logger.log_to_logs(f"❌ FallbackAgent error: {str(e)}")
            channel_logger.log_to_logs("🛡️ FallbackAgent using emergency T3RN malfunction response")
            
            # Use emergency T3RN malfunction messages instead of failing
            import random
            from agents.agent_prompts import T3RN_MALFUNCTION_MESSAGES
            
            emergency_response = random.choice(T3RN_MALFUNCTION_MESSAGES)
            
            result = AgentResult()
            result.final_answer = emergency_response
            result.error_content = ""
            
            return result