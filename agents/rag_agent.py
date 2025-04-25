# rag_agent.py (using recursive chunking)

import os
from autogen import AssistantAgent
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
import json

# Load vectorstore using recursive chunking

def load_vector_knowledge(knowledge_path: str) -> FAISS:
    if not os.path.exists(knowledge_path):
        os.makedirs(os.path.dirname(knowledge_path), exist_ok=True)
        default_knowledge = """
        ## ETFs
        - VTI (Vanguard Total Stock Market): Broad US stock market exposure, medium risk
        - BND (Vanguard Total Bond): US bond market exposure, low risk
        - VXUS (Vanguard Total International Stock): International stock exposure, medium-high risk

        ## Robo-Advisors
        - Betterment: Automated investing with tax optimization, adjustable risk
        - Wealthfront: Automated investing with financial planning tools, adjustable risk

        Fidelity® U.S. Bond Index Fund
        VRS Code: 002326
        Gross Expense Ratio: 0.025% as of 10/30/2024
        Fund Objective: Seeks to provide investment results that correspond to the aggregate price and interest performance of the debt securities in the Bloomberg U.S. Aggregate Bond Index.
        Fund Strategy: Normally investing at least 80% of the fund’s assets in bonds included in the Bloomberg U.S. Aggregate Bond Index...
        """
        with open(knowledge_path, "w") as f:
            f.write(default_knowledge)

    with open(knowledge_path, "r") as f:
        raw_text = f.read()

    # Use RecursiveCharacterTextSplitter for smart chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = splitter.split_text(raw_text)
    documents = [Document(page_content=chunk) for chunk in chunks]

    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(documents, embeddings)
    return vectorstore


def goal_json_to_query(json_str: str) -> str:
    try:
        goal = json.loads(json_str)
        goal_type = goal.get("goal_type", "a general goal")
        horizon = goal.get("investment_horizon", "a medium-term horizon")
        risk = goal.get("risk_tolerance", "moderate")
        preferences = goal.get("investment_preferences", [])
        pref_text = ", ".join(preferences) if preferences else "no specific preferences"

        return (
            f"I want to invest for {goal_type} with {risk} risk and {horizon}, and I prefer {pref_text}."
        )
    except Exception:
        return "I want to invest for a general purpose with moderate risk and no specific preferences."


# Create the RAG Agent

def get_rag_agent(config_list, knowledge_path, user_goal_json, top_k: int = 10):
    vectorstore = load_vector_knowledge(knowledge_path)

    user_goal_text = goal_json_to_query(json.dumps(user_goal_json))

    print("Goal text used for search: "+user_goal_text)

    retrieved_docs = vectorstore.similarity_search(user_goal_text, top_k)
    knowledge_text = "\n\n".join([doc.page_content for doc in retrieved_docs])

    print("Knowledge text from vector search: \n"+knowledge_text)

    rag_agent = AssistantAgent(
        name="RAGAgent",
        llm_config={
            "config_list": config_list,
            "temperature": 0.1
        },
        system_message=f"""You are a financial investment advisor implementing the Retrieval Augmented Generation pattern.
        
        Given a structured goal JSON, use the investment knowledge base to identify suitable investment options.
        The knowledge base contains information about various ETFs, robo-advisors, and investment strategies.
        
        RELEVANT INVESTMENT KNOWLEDGE BASE:
        {knowledge_text}
        
        Based on the user's goals, provide:
        1. A list of suitable investment products (ETFs or robo-advisors). Select at least 4 products.
        2. Current market insights relevant to the user's goals
        3. A summary of the key considerations
        
        Format your response as a JSON object with the following structure:
        {{
            "products": [
                {{"name": "...", "type": "...", "risk_level": "...", "description": "..."}}
            ],
            "market_insights": "...",
            "key_considerations": "..."
        }}
        """
    )

    return rag_agent

# Test the goal_json_to_query function
if __name__ == "__main__":
    print("Generated query:")
    test_json = json.dumps({
        "goal_type": "education",
        "investment_horizon": "long-term",
        "risk_tolerance": "low",
        "investment_preferences": []
    })
    print("Generated query:")
    print(goal_json_to_query(test_json))


# # Import autogen
# import autogen
# from autogen import AssistantAgent, UserProxyAgent
# import os

# def get_rag_agent(config_list,knowledge_path):

#     knowledge_base = load_knowledge_base(knowledge_path)

#     rag_agent = AssistantAgent(
#         name="RAGAgent",
#         llm_config={
#             "config_list": config_list,
#             "temperature": 0.1
#         },
#         system_message=f"""You are a financial investment advisor implementing the Retrieval Augmented Generation pattern.
        
#         Given a structured goal JSON, use the investment knowledge base to identify suitable investment options.
#         The knowledge base contains information about various ETFs, robo-advisors, and investment strategies.
        
#         INVESTMENT KNOWLEDGE BASE:
#         {knowledge_base}
        
#         Based on the user's goals, provide:
#         1. A list of suitable investment products (ETFs or robo-advisors)
#         2. Current market insights relevant to the user's goals
#         3. A summary of the key considerations
        
#         Format your response as a JSON object with the following structure:
#         {{
#             "products": [
#                 {{"name": "...", "type": "...", "risk_level": "...", "description": "..."}}
#             ],
#             "market_insights": "...",
#             "key_considerations": "..."
#         }}
#         """
#     )

#     return rag_agent

# def load_knowledge_base(knowledge_path):
#     """Load the investment knowledge base."""
#     # knowledge_path = "data/investment_knowledge.txt"
#     knowledge_path = knowledge_path 
    
#     if os.path.exists(knowledge_path):
#         with open(knowledge_path, "r") as f:
#             return f.read()
#     else:
#         # Create a basic knowledge base if the file doesn't exist
#         os.makedirs(os.path.dirname(knowledge_path), exist_ok=True)
        
#         knowledge_base = """
#         # Basic Investment Knowledge
        
#         ## ETFs
#         - VTI (Vanguard Total Stock Market): Broad US stock market exposure, medium risk
#         - BND (Vanguard Total Bond): US bond market exposure, low risk
#         - VXUS (Vanguard Total International Stock): International stock exposure, medium-high risk
        
#         ## Robo-Advisors
#         - Betterment: Automated investing with tax optimization, adjustable risk
#         - Wealthfront: Automated investing with financial planning tools, adjustable risk
#         """
        
#         with open(knowledge_path, "w") as f:
#             f.write(knowledge_base)
        
#         return knowledge_base