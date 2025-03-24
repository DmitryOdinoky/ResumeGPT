# import modules
import os
import pandas as pd
import openai
from openai import InvalidRequestError
import time
import json
from json import JSONDecodeError
from tqdm import tqdm
# add a progress bar to pandas operations
tqdm.pandas(desc='CVs')

# define the path to the output CSV file
output_csv_file_path = '../Output/CVs_Info_Extracted.csv'

# define the path to the output Excel file
output_excel_file_path = '../Output/CVs_Info_Extracted.xlsx'


# define a class to extract CV information
class CVsInfoExtractor:
    # define a constructor that initializes the class with a DataFrame of CVs
    def __init__(self, cvs_df, openai_api_key, desired_positions):
        self.cvs_df = cvs_df
        
        # open a file in read mode and read the contents of the file into a variable
        with open('../Engineered_Prompt/Prompt.txt', 'r') as file:
            self.prompt = file.read()
        
        # Join the desired positions into a comma-separated string
        suitable_positions_str = "(" + ", ".join(desired_positions) + ")"

        # Replace the placeholder in the prompt with the formatted suitable positions string
        self.prompt = self.prompt.replace('(suitable position for the candidate)', suitable_positions_str)
        
        
        # set the OpenAI API key
        openai.api_key = openai_api_key


    # define internal function to call GPT for CV info extraction
    def _call_gpt_for_cv_info_extraction(self, prompt, cv_content, model, temperature = 0):

        # create a dict of parameters for the ChatCompletion API
        completion_params = {
            'model': model,
            'messages': [{"role": "system", "content": prompt},
                        {"role": "user", "content": cv_content}],
            'temperature': temperature}

        # send a request to the ChatCompletion API and store the response
        response = openai.ChatCompletion.create(**completion_params)
        # if the response contains choices and at least one choice, extract the message content
        if 'choices' in response and len(response.choices) > 0:
            cleaned_response = response['choices'][0]['message']['content']
            try:
                # try to convert the message content to a JSON object
                json_response = json.loads(cleaned_response)
            except JSONDecodeError:
                # if the conversion fails, set the JSON response to None
                json_response = None  
        else:
            # if the response does not contain choices or no choice, set the JSON response to None
            json_response = None
            
        # return the JSON response
        return json_response
    
    
    # Defines internal function to normalize a JSON response from GPT
    def _normalize_gpt_json_response(self, CV_Filename, json_response):
        CV_Filename_df = pd.DataFrame([CV_Filename], columns=['CV_Filename'])
        df_CV_Info_Json = pd.DataFrame([[json_response]], columns=['All_Info_JSON'])
        
        if json_response is None:
            print(f"Warning: No valid JSON for {CV_Filename}, skipping normalization.")
            df_CV_Info_Json_normalized = pd.DataFrame([{}])  # Empty dict to avoid empty DataFrame issues
        elif isinstance(json_response, list):
            print(f"Warning: JSON for {CV_Filename} is a list, normalizing first item.")
            df_CV_Info_Json_normalized = pd.json_normalize(json_response[0] if json_response else {})
        else:
            df_CV_Info_Json_normalized = pd.json_normalize(json_response)
        
        # Ensure "University Education" exists and is a list; if not, set to empty list
        if 'University Education' not in df_CV_Info_Json_normalized.columns:
            df_CV_Info_Json_normalized['University Education'] = [[]]
        elif not isinstance(df_CV_Info_Json_normalized['University Education'].iloc[0], list):
            df_CV_Info_Json_normalized['University Education'] = [[]]
        
        # Ensure "Languages" exists and is a list; if not, set to empty list
        if 'Languages' not in df_CV_Info_Json_normalized.columns:
            df_CV_Info_Json_normalized['Languages'] = [[]]
        elif not isinstance(df_CV_Info_Json_normalized['Languages'].iloc[0], list):
            df_CV_Info_Json_normalized['Languages'] = [[]]
        
        # Ensure "Email" exists and is a string; if not, set to empty string
        if 'Email' not in df_CV_Info_Json_normalized.columns:
            df_CV_Info_Json_normalized['Email'] = ""
        elif not isinstance(df_CV_Info_Json_normalized['Email'].iloc[0], str):
            df_CV_Info_Json_normalized['Email'] = ""
        
        # Ensure "Phone Number" exists and is a string; if not, set to empty string
        if 'Phone Number' not in df_CV_Info_Json_normalized.columns:
            df_CV_Info_Json_normalized['Phone Number'] = ""
        elif not isinstance(df_CV_Info_Json_normalized['Phone Number'].iloc[0], str):
            df_CV_Info_Json_normalized['Phone Number'] = ""
        
        # Ensure "Top 3 Technical Skills" exists and is a list; if not, set to empty list
        if 'Top 3 Technical Skills' not in df_CV_Info_Json_normalized.columns:
            df_CV_Info_Json_normalized['Top 3 Technical Skills'] = [[]]
        elif not isinstance(df_CV_Info_Json_normalized['Top 3 Technical Skills'].iloc[0], list):
            df_CV_Info_Json_normalized['Top 3 Technical Skills'] = [[]]
        
        # If "Top 3 Technical Skills" is empty, try to extract skills from "Top 5 Courses/Certifications"
        tech_skills = df_CV_Info_Json_normalized['Top 3 Technical Skills'].iloc[0]
        if not tech_skills:  # If empty list
            courses = df_CV_Info_Json_normalized.get('Top 5 Courses/Certifications', [[]]).iloc[0]
            if isinstance(courses, list) and courses:
                # Simple heuristic: extract keywords that might indicate technical skills
                extracted_skills = []
                for course in courses:
                    course_lower = str(course).lower()
                    if 'python' in course_lower:
                        extracted_skills.append('Python')
                    if 'sql' in course_lower:
                        extracted_skills.append('SQL')
                    if 'aws' in course_lower:
                        extracted_skills.append('AWS')
                    if 'java' in course_lower:
                        extracted_skills.append('Java')
                    if 'machine learning' in course_lower:
                        extracted_skills.append('Machine Learning')
                    # Add more mappings as needed
                # Take top 3 unique skills
                extracted_skills = list(dict.fromkeys(extracted_skills))[:3]
                df_CV_Info_Json_normalized['Top 3 Technical Skills'] = [extracted_skills]
        
        # Ensure "Suitable Position" exists and is a list of dictionaries; if not, set to empty list
        if 'Suitable Position' not in df_CV_Info_Json_normalized.columns:
            df_CV_Info_Json_normalized['Suitable Position'] = [[]]
        elif not isinstance(df_CV_Info_Json_normalized['Suitable Position'].iloc[0], list):
            df_CV_Info_Json_normalized['Suitable Position'] = [[]]
        else:
            # Validate the format of "Suitable Position" entries
            suitable_positions = df_CV_Info_Json_normalized['Suitable Position'].iloc[0]
            validated_positions = []
            for pos in suitable_positions:
                if (isinstance(pos, dict) and 
                    'position' in pos and isinstance(pos['position'], str) and 
                    'suitability' in pos and isinstance(pos['suitability'], (int, float)) and 
                    0.0 <= pos['suitability'] <= 1.0):
                    validated_positions.append(pos)
            df_CV_Info_Json_normalized['Suitable Position'] = [validated_positions]
        
        df = pd.concat([CV_Filename_df, df_CV_Info_Json_normalized, df_CV_Info_Json], axis=1)
        return df


    # Defines internal function to write the DataFrame into a CSV file
    def _write_response_to_file(self, df):

        # Checks if the output CSV file already exists
        if os.path.isfile(output_csv_file_path):
            # If the file exists, append the DataFrame into the CSV file without writing headers
            df.to_csv(output_csv_file_path, mode='a', index=False, header=False)
        else:
            # If the file doesn't exist, write the DataFrame into a new CSV file
            df.to_csv(output_csv_file_path, mode='w', index=False)


    # Define the internal function _gpt_pipeline
    def _gpt_pipeline(self, row, model='gpt-3.5-turbo'):
        CV_Filename = row['CV_Filename']
        CV_Content = row['CV_Content']
        time.sleep(5)
        
        try:
            print(f"Debug: CV Content for {CV_Filename}: {CV_Content[:200]}...")  # First 200 chars
            print('Calling GPT For CV Info Extraction...')
            json_response = self._call_gpt_for_cv_info_extraction(prompt=self.prompt, cv_content=CV_Content, model=model)
            print(f"Debug: JSON response for {CV_Filename}: {json_response}")
            
            print('Normalizing GPT Response...')
            df = self._normalize_gpt_json_response(CV_Filename, json_response)
            print('Appending Results To The CSV File...')
            self._write_response_to_file(df)
            print('----------------------------------------------')
            return json_response
        except InvalidRequestError as e:
            print('An Error Occurred:', str(e))
            print("Tokens don't fit gpt-3.5-turbo, calling gpt-4...")
            return self._gpt_pipeline(row, model='gpt-4')
        except Exception as e:
            print(f"Unexpected Error for {CV_Filename}: {str(e)}")
            return None


    # Define the internal function _write_final_results_to_excel
    def _write_final_results_to_excel(self):
        # Load the CSV file into a pandas DataFrame
        df_to_excel = pd.read_csv(output_csv_file_path)

        # Write the DataFrame to an Excel file
        df_to_excel.to_excel(output_excel_file_path)

        # Return the DataFrame
        return df_to_excel


    # Define the main function extract_cv_info
    def extract_cv_info(self):
        # Print a status message indicating the start of the ResumeGPT Pipeline
        print('---- Excecuting ResumeGPT Pipeline ----')
        print('----------------------------------------------')

        # Apply the _gpt_pipeline function to each row in cvs_df DataFrame
        self.cvs_df['CV_Info_Json'] = self.cvs_df.progress_apply(self._gpt_pipeline, axis=1)

        # Print a status message indicating the completion of the extraction
        print('Extraction Completed!')

        # Print a status message indicating that results are being saved to Excel
        print('Saving Results to Excel...')

        # Write the final results to an Excel file
        final_df = self._write_final_results_to_excel()

        # Return the final DataFrame
        return final_df
