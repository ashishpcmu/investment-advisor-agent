"""
Enhanced Investment Strategy Advisor API
This module extends the original Investment Strategy Advisor with FastAPI
to provide a RESTful API for the React frontend.
"""

import os
os.environ["AUTOGEN_USE_DOCKER"] = "False"

import json
import logging
import asyncio
import random
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Import autogen
import autogen
from autogen import AssistantAgent, UserProxyAgent

# Import agent modules
from agents.goal_creator_agent import get_goal_creator_agent
from agents.rag_agent import get_rag_agent
from agents.investment_specialist_agent import get_investment_specialist_agent
from agents.risk_specialist_agent import get_risk_specialist_agent
from agents.goal_specialist_agent import get_goal_specialist_agent
from agents.voting_coordinator_agent import get_voting_coordinator_agent
from agents.presentation_agent import get_presentation_agent
from agents.feedback_agent import get_feedback_agent
from agents.financial_data_agent import (
    get_financial_data_agent,
    analyze_investment_options,
    get_market_data_for_strategy,
    enhance_investment_recommendations
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")  # Or "gpt-4-turbo" for better results

# FastAPI app
app = FastAPI(
    title="Investment Strategy Advisor API",
    description="API for generating personalized investment strategies",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active advisors and their results
active_advisors = {}
recommendations = {}

# Pydantic models for request/response validation
class InvestmentGoalRequest(BaseModel):
    goal_text: str
    risk_tolerance: Optional[int] = 2
    investment_horizon: Optional[int] = 10
    portfolio_size: Optional[int] = 10000

class FeedbackRequest(BaseModel):
    recommendation_id: str
    feedback_text: str

class StrategyResponse(BaseModel):
    recommendation_id: str
    structured_goal: Dict[str, Any]
    strategy: Dict[str, Any]
    agent_insights: Dict[str, Any]
    presentation: str

class FeedbackResponse(BaseModel):
    recommendation_id: str
    feedback_analysis: Dict[str, Any]

def load_knowledge_base():
    """Load the investment knowledge base."""
    knowledge_path = "data/investment_knowledge.txt"
    
    if os.path.exists(knowledge_path):
        with open(knowledge_path, "r") as f:
            return f.read()
    else:
        # Create a basic knowledge base if the file doesn't exist
        os.makedirs(os.path.dirname(knowledge_path), exist_ok=True)
        
        knowledge_base = """
        # Basic Investment Knowledge
        
        ## ETFs
        - VTI (Vanguard Total Stock Market): Broad US stock market exposure, medium risk
        - BND (Vanguard Total Bond): US bond market exposure, low risk
        - VXUS (Vanguard Total International Stock): International stock exposure, medium-high risk
        
        ## Robo-Advisors
        - Betterment: Automated investing with tax optimization, adjustable risk
        - Wealthfront: Automated investing with financial planning tools, adjustable risk
        """
        
        with open(knowledge_path, "w") as f:
            f.write(knowledge_base)
        
        return knowledge_base

def convert_risk_tolerance_to_text(value):
    """Convert numeric risk tolerance to text representation."""
    if value == 1:
        return "low"
    elif value == 2:
        return "medium"
    else:
        return "high"

def convert_horizon_to_text(years):
    """Convert numeric investment horizon to text representation."""
    if years < 10:
        return "short-term"
    elif years <= 20:
        return "medium-term"
    else:
        return "long-term"

async def run_enhanced_investment_advisor(user_input, risk_tolerance, investment_horizon, portfolio_size):
    """Run the Enhanced Investment Strategy Advisor using autogen agents with financial data integration."""
    try:
        # Configure autogen
        config_list = [
            {
                "model": OPENAI_MODEL,
                "api_key": OPENAI_API_KEY,
            }
        ]
        
        # Load the knowledge base
        knowledge_base = load_knowledge_base()
        
        # Convert numerical values to text for the agents
        risk_text = convert_risk_tolerance_to_text(risk_tolerance)
        horizon_text = convert_horizon_to_text(investment_horizon)
        
        # Enhance user input with structured data if not already included
        enhanced_input = f"{user_input}\n\nMy risk tolerance is {risk_text}. My investment horizon is {investment_horizon} years. My portfolio size is ${portfolio_size}."
        
        # Step 1: Extract structured goal - Passive Goal Creator pattern
        logger.info("Step 1: Extracting investment goals...")
        goal_creator = get_goal_creator_agent(config_list)
        
        user_proxy = UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0
        )
        
        # Extract structured goal
        user_proxy.initiate_chat(
            goal_creator, 
            message=enhanced_input
        )
        
        goal_creator_response = goal_creator.last_message()["content"]
        
        # Extract the JSON object from the response
        try:
            json_start = goal_creator_response.find('{')
            json_end = goal_creator_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                structured_goal = json.loads(goal_creator_response[json_start:json_end])
                logger.info(f"Structured goal: {json.dumps(structured_goal, indent=2)}")
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Error extracting structured goal: {e}")
            return None
        
        # Ensure the structured goal has the correct risk and horizon based on input parameters
        structured_goal["risk_tolerance"] = risk_text
        structured_goal["investment_horizon"] = horizon_text
        
        # Step 2: Get real-time market data - Financial Data Agent
        logger.info("Step 2: Retrieving market data and financial analysis...")
        
        market_data = get_market_data_for_strategy(config_list, structured_goal)
        
        # Create financial insights text for the RAG agent
        financial_insights = f"""
        # Current Market Data & Financial Analysis
        
        ## Market Sectors
        {market_data.get('analysis', 'No sector data available.')}
        
        ## Risk Profile Analysis
        Risk tolerance: {market_data.get('risk_tolerance', 'medium')}
        Symbols analyzed: {', '.join(market_data.get('symbols_analyzed', []))}
        """
        
        # Step 3: Retrieve investment options - RAG pattern with financial data
        logger.info("Step 3: Retrieving investment options...")
        
        knowledge_path = "data/investment_knowledge.txt"
        rag_agent = get_rag_agent(config_list, knowledge_path, structured_goal)
        
        # Get investment options
        user_proxy.initiate_chat(
            rag_agent, 
            message=f"Based on this structured goal and current market data, what investment options would you recommend? {json.dumps(structured_goal)}"
        )
        
        rag_response = rag_agent.last_message()["content"]
        
        # Extract the JSON object from the response
        try:
            json_start = rag_response.find('{')
            json_end = rag_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                investment_options = json.loads(rag_response[json_start:json_end])
                logger.info(f"Found {len(investment_options.get('products', []))} investment options")
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Error extracting investment options: {e}")
            return None
        
        # Step 4: Voting-Based Cooperation pattern
        logger.info("Step 4: Collecting votes from specialists...")
        
        # Investment Specialist
        investment_specialist = get_investment_specialist_agent(config_list)
        
        # Get votes from Investment Specialist
        user_proxy.initiate_chat(
            investment_specialist, 
            message=f"""
            Please evaluate these investment options based on returns and diversification: 
            
            Goal: {json.dumps(structured_goal)}
            Options: {json.dumps(investment_options)}
            
            Current Market Data:
            {financial_insights}
            """
        )
        
        investment_response = investment_specialist.last_message()["content"]
        
        # Extract the JSON object from the response
        try:
            json_start = investment_response.find('{')
            json_end = investment_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                investment_votes = json.loads(investment_response[json_start:json_end])
                logger.info("Received votes from Investment Specialist")
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Error extracting investment votes: {e}")
            return None
        
        # Risk Specialist
        risk_specialist = get_risk_specialist_agent(config_list)
        
        # Get votes from Risk Specialist
        user_proxy.initiate_chat(
            risk_specialist, 
            message=f"""
            Please evaluate these investment options based on risk alignment: 
            
            Goal: {json.dumps(structured_goal)}
            Options: {json.dumps(investment_options)}
            
            Current Market Data:
            {financial_insights}
            """
        )
        
        risk_response = risk_specialist.last_message()["content"]
        
        # Extract the JSON object from the response
        try:
            json_start = risk_response.find('{')
            json_end = risk_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                risk_votes = json.loads(risk_response[json_start:json_end])
                logger.info("Received votes from Risk Specialist")
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Error extracting risk votes: {e}")
            return None
        
        # Goal Specialist
        goal_specialist = get_goal_specialist_agent(config_list)
        
        # Get votes from Goal Specialist
        user_proxy.initiate_chat(
            goal_specialist, 
            message=f"""
            Please evaluate these investment options based on goal alignment: 
            
            Goal: {json.dumps(structured_goal)}
            Options: {json.dumps(investment_options)}
            
            Current Market Data:
            {financial_insights}
            """
        )
        
        goal_response = goal_specialist.last_message()["content"]
        
        # Extract the JSON object from the response
        try:
            json_start = goal_response.find('{')
            json_end = goal_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                goal_votes = json.loads(goal_response[json_start:json_end])
                logger.info("Received votes from Goal Specialist")
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Error extracting goal votes: {e}")
            return None
        
        # Step 5: Vote Coordination - Finalize strategy
        logger.info("Step 5: Coordinating votes and generating final strategy...")
        
        voting_coordinator = get_voting_coordinator_agent(config_list)
        
        # Get final strategy
        user_proxy.initiate_chat(
            voting_coordinator, 
            message=f"""
            Please create a final investment strategy based on the following votes:
            
            Goal: {json.dumps(structured_goal)}
            Options: {json.dumps(investment_options)}
            
            Investment Specialist votes: {json.dumps(investment_votes)}
            Risk Specialist votes: {json.dumps(risk_votes)}
            Goal Specialist votes: {json.dumps(goal_votes)}
            
            Current Market Data:
            {financial_insights}
            """
        )
        
        coordinator_response = voting_coordinator.last_message()["content"]
        
        # Extract the JSON object from the response
        try:
            json_start = coordinator_response.find('{')
            json_end = coordinator_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                strategy = json.loads(coordinator_response[json_start:json_end])
                logger.info("Final strategy generated")
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Error extracting strategy: {e}")
            return None
        
        # Step 6: Enhance strategy with real-time financial data
        logger.info("Step 6: Enhancing strategy with real-time financial data...")
        
        enhanced_strategy = enhance_investment_recommendations(config_list, strategy, structured_goal)
        
        # Step 7: Format the presentation
        logger.info("Step 7: Formatting presentation...")
        
        presentation_agent = get_presentation_agent(config_list)
        
        # Get formatted presentation
        user_proxy.initiate_chat(
            presentation_agent, 
            message=f"""
            Please format this enhanced investment strategy for presentation to the user:
            
            {json.dumps(enhanced_strategy)}
            
            Include all the real-time financial data and market insights in your presentation.
            """
        )
        
        presentation = presentation_agent.last_message()["content"]
        
        # Create agent insights for frontend
        agent_insights = {
            "risk_agent_score": random.randint(6, 9),  # Simulated risk score
            "goal_agent_confidence": round(random.uniform(0.7, 0.95), 2),  # Simulated confidence
            "investment_agent_prediction": f"{random.randint(5, 12)}% annual return"  # Simulated prediction
        }
        
        # Return the results with all required data
        return {
            "structured_goal": structured_goal,
            "investment_options": investment_options,
            "strategy": enhanced_strategy,
            "agent_insights": agent_insights,
            "presentation": presentation,
            "market_data": financial_insights
        }
    
    except Exception as e:
        logger.error(f"Error in advisor process: {e}")
        return None

async def process_feedback(recommendation_id, feedback_text):
    """Process user feedback on the investment strategy."""
    try:
        if recommendation_id not in recommendations:
            return {"error": "Recommendation ID not found"}
        
        recommendation_data = recommendations[recommendation_id]
        
        # Configure autogen
        config_list = [
            {
                "model": OPENAI_MODEL,
                "api_key": OPENAI_API_KEY,
            }
        ]
        
        logger.info(f"Processing feedback for recommendation {recommendation_id}...")
        
        # Create the feedback agent
        feedback_agent = get_feedback_agent(config_list)
        
        user_proxy = UserProxyAgent(
            name="User",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=0
        )
        
        # Process the feedback
        user_proxy.initiate_chat(
            feedback_agent, 
            message=f"""
            Process this feedback on an investment recommendation:
            
            Original Goal: {json.dumps(recommendation_data.get('structured_goal', {}))}
            Recommended Strategy: {json.dumps(recommendation_data.get('strategy', {}))}
            User Feedback: {feedback_text}
            
            Current Market Data:
            {recommendation_data.get('market_data', '')}
            """
        )
        
        feedback_response = feedback_agent.last_message()["content"]
        
        # Extract the JSON object from the response
        try:
            json_start = feedback_response.find('{')
            json_end = feedback_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(feedback_response[json_start:json_end])
                
                # Store feedback analysis
                recommendations[recommendation_id]["feedback_analysis"] = analysis
                
                return analysis
            else:
                raise ValueError("Failed to extract JSON from response")
        except Exception as e:
            logger.error(f"Error extracting feedback analysis: {e}")
            return {
                "error": f"Error analyzing feedback: {str(e)}",
                "feedback_analysis": "Unable to analyze feedback properly.",
                "risk_adjustment": "no change",
                "preference_changes": [],
                "strategy_adjustments": []
            }
    
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        return {"error": str(e)}

@app.post("/api/generate-strategy", response_model=StrategyResponse)
async def generate_strategy(request: InvestmentGoalRequest):
    """Generate an investment strategy based on the user's goal."""
    try:
        # Generate a recommendation ID
        recommendation_id = f"rec_{len(recommendations) + 1}_{int(asyncio.get_event_loop().time())}"
        
        # Run the investment advisor
        result = await run_enhanced_investment_advisor(
            request.goal_text,
            request.risk_tolerance,
            request.investment_horizon,
            request.portfolio_size
        )
        
        if not result:
            raise HTTPException(status_code=500, detail="Failed to generate investment strategy")
        
        # Store the recommendation for later reference
        recommendations[recommendation_id] = result
        
        # Return the strategy response
        return {
            "recommendation_id": recommendation_id,
            "structured_goal": result["structured_goal"],
            "strategy": result["strategy"],
            "agent_insights": result["agent_insights"],
            "presentation": result["presentation"]
        }
    
    except Exception as e:
        logger.error(f"Error generating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-feedback", response_model=Dict[str, Any])
async def feedback_analysis(request: FeedbackRequest):
    """Process feedback on an investment strategy."""
    try:
        if request.recommendation_id not in recommendations:
            raise HTTPException(status_code=404, detail="Recommendation not found")
        
        # Process the feedback
        analysis = await process_feedback(request.recommendation_id, request.feedback_text)
        
        if not analysis or "error" in analysis:
            raise HTTPException(status_code=500, detail=analysis.get("error", "Failed to analyze feedback"))
        
        return analysis
    
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """API health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
