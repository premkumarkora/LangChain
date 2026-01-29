from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


load_dotenv()
tools = []

llm = ChatOpenAI(model="gpt-4o-mini" , temperature=0)
agent_executor = create_react_agent(llm, tools)



# Stream the agent's thoughts
for chunk in agent_executor.stream({"messages": [("user", "your question")]}):
    print(chunk)

    