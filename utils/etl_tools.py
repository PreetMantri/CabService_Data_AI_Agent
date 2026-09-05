import os,requests
import pandas as pd

class ETLTools:

    def __init__(self):
        pass

    def extract_load(self, url:str, output_folder:str, format:str):
        """
        This tool extracts the data from the API (url) and loads it into the desired location (destination).

        Args:
            url (str): The API endpoint from which to extract data.
            output_folder (str): The destination folder where the extracted data will be saved.
            format (str): The format in which to save the extracted data. Can be "json", "csv", or "parquet".
        Returns:
            str: A message indicating the success or failure of the operation.    
        """

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        output_folder = os.path.join(project_root, output_folder)

        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses (4xx and 5xx)
            data = response.json()  # Assuming the API returns JSON data
            filename = os.path.join(output_folder, f"extracted_data.{format}")
            os.makedirs(output_folder, exist_ok=True)  # Create the output folder if it doesn't exist

            df = pd.json_normalize(data['results'])  # Normalize semi-structured JSON data into a flat table
            if format == "json":
                df.to_json(filename, orient='records', lines=True)
            elif format == "csv":
                df.to_csv(filename, index=False)
            elif format == "parquet":
                df.to_parquet(filename, index=False)
            else:
                return f"Unsupported format: {format}. Please choose 'json', 'csv', or 'parquet'."

            return f"Data extracted and saved to {filename} successfully."
        except requests.exceptions.RequestException as e:
            return f"Error extracting data from {url}: {e}"


    def transform_load_context(self,file_path:str):
        """
        This tool transforms the data from the file (file_path) and loads it into the desired location (destination).

        Args:
            file_path (str): The path to the file containing the data to be transformed.
        Returns:
            str: A message indicating the success or failure of the operation.    
        """

        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == ".csv":
            df = pd.read_csv(file_path)
        elif file_extension == ".json":
            df = pd.read_json(file_path)
        elif file_extension == ".parquet":
            df = pd.read_parquet(file_path)
        else:
            return f"Unsupported file format: {file_extension}. Please provide a CSV, JSON, or Parquet file." 

        top_3_rows = str(df.head(3)) #Transform the data by getting the top 3 rows of the DataFrame 

        return top_3_rows

    def execute_code(self, code:str):
        """
        This tool executes the provided code and returns the output.

        Args:
            code (str): The code to be executed.
        Returns:
            str: The output of the executed code or an error message if execution fails.
        """
        try:
            exec(code)
            return "Code executed successfully."
        except Exception as e:
            return f"Error executing code: {e}"

if __name__ == "__main__":
    obj = ETLTools()
    path= "C:\\Users\\preet\\Downloads\\DATA_AGENT\\data\\extract\\extracted_data.csv"
    # print(obj.extract_load("https://pokeapi.co/api/v2/pokemon","data/extract","csv"))
    print(obj.transform_load_context(path))


         
