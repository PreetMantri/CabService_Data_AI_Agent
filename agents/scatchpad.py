import os, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from Models.schema import AgentSchema, JudgeSchema
from langchain_core.messages import HumanMessage 

llm = pick_llm("medium") 
llm_judge = llm.with_structured_output(JudgeSchema)

sql_query = "SELECT * FROM users WHERE age > 30;"
prompt = """
You are an SQL Judge agent for data security. Your task is to evaluate the safety of the generated SQL query.
The SQL query should only be used for data retrieval and should not perform any data manipulation or modification operations.
Neither the SQL qury should contain any data manipulation or modification operations such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, etc. If the SQL query is safe and doest perfrom any modififcations on the database and only reads the data, return "Yes" and provide a brief comment on why it is safe. If the SQL query is unsafe, return "No" and provide a brief comment on why it is unsafe and without revealing any variables or sensitive information.
Here is the SQL query to evaluate:
{sql_query}
"""

response = llm_judge.invoke(prompt).model_dump() #Get the result as a dictionary
print(response)

