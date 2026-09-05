import re
import os, sys

from langchain_core.messages import AIMessage, HumanMessage 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.llm_pick import pick_llm
from utils.database import DatabaseUtil
from Models.schema import AgentSchema, JudgeSchema
from langgraph.graph import StateGraph, START, END

#---------------------------------------- AI Agent Code ----------------------------------------#

def curate_ques(state: AgentSchema) -> AgentSchema:

    user_question = state.user_question # Pydantic MOdel Object

    llm = pick_llm("low") 
    response = llm.invoke(f"Curate the following user question : {user_question}").content  #Generate curated question using the prompt

    state.curated_ques = str(response)
    state.messages = state.messages + [HumanMessage(content = f"{response}")]  #Append the curated question to the messages list
    return state

def prompt_query_context(state: AgentSchema) -> AgentSchema:

    curated_ques = state.curated_ques # Pydantic MOdel Object

    # Get the database schema details
    conn_details = {
        'host': os.environ['host'],
        'port': os.environ['port'],
        'user': os.environ['user'],
        'password': os.environ['password'],
        'database': os.environ['database']
    }

    obj = DatabaseUtil(conn_details)
    schema_info = obj.schema_details("public")  # Assuming the schema name is 'public'

    # Create a detailed prompt with SQL DB Context
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language
    query into Postgres SQL query that can be executed on the database. You are provided
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.

    User's Original Question: {curated_ques}
    Database Schema Details: 
    {schema_info}
    """
    state.prompt_query_context = prompt
    return state

def extract_raw_sql(raw_output) -> str:
    # 1. Handle list of dicts (multimodal LLM response)
    if isinstance(raw_output, list) and len(raw_output) > 0:
        raw_text = raw_output[0].get("text", "")
    elif isinstance(raw_output, str):
        raw_text = raw_output
    else:
        raw_text = str(raw_output)

    # 2. Extract content between ```sql and ``` if present
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 3. Fallback: clean any trailing/leading backticks
    return raw_text.strip("` \n")

# Generate SQL Query Node:
def generate_sql_query(state: AgentSchema) -> AgentSchema:
    prompt = state.prompt_query_context # Pydantic MOdel Object
    llm = pick_llm("medium") #Pick a medium LLM for generating SQL query
    generated_sql_query = llm.invoke(prompt).content  #Generate SQL query using the prompt
    generated_sql_query = extract_raw_sql(generated_sql_query)  #Extract the raw SQL query
    print(f"Generated SQL Query: {generated_sql_query}")  #Print the generated SQL query for debugging
    state.generated_sql_query = generated_sql_query
    return state
    

# Is Safe Node:
# It checks if the generated SQL query is safe to execute on the database. It ensures that the query does not contain any data manipulation or modification operations such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, etc. If the SQL query is safe and only reads the data, it returns "Yes" along with a brief comment on why it is safe. If the SQL query is unsafe, it returns "No" along with a brief comment on why it is unsafe without revealing any variables or sensitive information.
def is_safe_sql(state: AgentSchema) -> AgentSchema:
    sql_query = state.generated_sql_query
    llm = pick_llm("medium") 
    llm_judge = llm.with_structured_output(JudgeSchema)

    #sql_query = "SELECT * FROM users WHERE age > 30;"
    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.
    Here's the SQL query to evaluate:
    {sql_query}
    """

    response = llm_judge.invoke(prompt).model_dump() #Get the result as a dictionary
    state.is_safe = response['answer']
    state.comments = response['comments']

    return state

# Cancelled SQL Query Node:
# If the generated SQL query is deemed unsafe, this node will cancel the execution of the SQL

def cancelled_sql(state: AgentSchema) -> AgentSchema:

    comments = state.comments # Pydantic MOdel Object
    state.final_answer = f"The generated SQL query is unsafe to execute. Reason: . Therefore, the reason provided by the judge is : {comments}. Therefore, the execution of the SQL query has been cancelled."
    state.messages = state.messages + [AIMessage(content = f"{state.final_answer}")]  #Append the final answer to the messages list
    return state


# Execute SQL Query Node:
# If the generated SQL query is deemed safe, this node will execute the SQL query on the database and return the result.

def execute_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query # Pydantic MOdel Object
    conn_details = {
        'host': os.environ['host'],
        'port': os.environ['port'],
        'user': os.environ['user'],
        'password': os.environ['password'],
        'database': os.environ['database']
    }

    obj = DatabaseUtil(conn_details)
    execution_result = obj.execute_query(sql_query)  # Execute the SQL query on the database
    state.sql_query_execution_result = str(execution_result)
    return state

# Represent Final Answer Node:
# This node will represent the final answer to the user based on the execution result of the SQL query.
def represent_final_answer(state: AgentSchema) -> AgentSchema:

    execution_result = state.sql_query_execution_result # Pydantic MOdel Object
    curated_ques = state.curated_ques

    llm = pick_llm("low") #Pick a low LLM for generating final answer
    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the execution result of the SQL query.
    The final answer should be a concise and clear response to the user's original question, based on the execution result of the SQL query. The final answer should be in natural language and should not contain any SQL queries or technical jargon. The final answer should be easy to understand for a non-technical user. \n
    User's Original Question: {curated_ques} \n
    Execution Result: {execution_result}
    """

    llm_response = llm.invoke(prompt).content  #Generate final answer using the prompt
    state.final_answer = str(llm_response)
    state.messages = state.messages + [AIMessage(content = f"{llm_response}")]  #Append the final answer to the messages list
    return state

# -----------------------------------------Graph Building---------------------------------------------------------------#
sql_agent_graph = StateGraph(AgentSchema)

# Nodes
sql_agent_graph.add_node(curate_ques, name="curate_ques")
sql_agent_graph.add_node(prompt_query_context, name="prompt_query_context")
sql_agent_graph.add_node(generate_sql_query, name="generate_sql_query")
sql_agent_graph.add_node(is_safe_sql, name="is_safe_sql")
sql_agent_graph.add_node(cancelled_sql, name="cancelled_sql")
sql_agent_graph.add_node(execute_sql, name="execute_sql")
sql_agent_graph.add_node(represent_final_answer, name="represent_final_answer")


#Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql_query")
sql_agent_graph.add_edge("generate_sql_query", "is_safe_sql")

# Conditional Edges based on the safety of the SQL query
def is_safe_sql_edge(state: AgentSchema) -> str:
    is_safe = state.is_safe
    if is_safe.lower() == "yes":
        return "execute_sql"
    else:
        return "cancelled_sql"

sql_agent_graph.add_conditional_edges("is_safe_sql", is_safe_sql_edge,
                                      {
                                          "execute_sql": "execute_sql",
                                          "cancelled_sql": "cancelled_sql"
                                      })

# sql_agent_graph.add_edge("is_safe_sql", "execute_sql")
# sql_agent_graph.add_edge("is_safe_sql", "cancelled_sql")

sql_agent_graph.add_edge("cancelled_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)


sql_analyst = sql_agent_graph.compile()

if __name__ == "__main__":
    #Compile the graph
    

    #Optionally, you can visualize the graph and save it as an image
    from IPython.display import display, Image
    img = Image(sql_analyst.get_graph().draw_mermaid_png())
    with open("sql_agent_graph.png", "wb") as f:
        f.write(img.data)

    input_schema = {
        "messages": [],
        "user_question": "What are the different types of Payment Methods we have in our database?",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    #Execute the graph with the input schema
    sql_analyst_response = sql_analyst.invoke(input_schema)
    print(sql_analyst_response['messages'])  # Print the final output of the graph execution
    print("********************************")

    print(sql_analyst_response['generated_sql_query'])  # Print the generated SQL query

    print("********************************")

    print(sql_analyst_response['sql_query_execution_result'])  # Print the result of executing the SQL query

    print("********************************")

    print(sql_analyst_response['prompt_query_context'])  # Print the prompt query context




