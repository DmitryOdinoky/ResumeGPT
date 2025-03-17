# import modules
import os
import pandas as pd
from tqdm import tqdm
from pdf2image import convert_from_path
import pytesseract
from PIL import Image


# Define a class to read CVs from a directory
class CVsReader:
    
    # Initialize the class with the directory path where CVs are located
    def __init__(self, cvs_directory_path):
        self.cvs_directory_path = cvs_directory_path

    # Method to read new CV files from the given directory
    def _read_new_directory_files(self):
        # Store the directory path of CVs
        cvs_directory_path = self.cvs_directory_path

        # Store the path of the CSV file where previously extracted CVs are stored
        previously_extracted_cvs_path = '../Output/CVs_Info_Extracted.csv'

        # Get a list of all files in the CVs directory
        all_cvs = os.listdir(cvs_directory_path)

        # If there is a CSV file of previously extracted CVs
        if os.path.isfile(previously_extracted_cvs_path):
            # Read that file and get the filenames of CVs
            previously_extracted_cvs = pd.read_csv(previously_extracted_cvs_path, usecols=['CV_Filename'])
            # Convert those filenames to a list
            previously_extracted_cvs = previously_extracted_cvs.CV_Filename.to_list()
            # Filter out the CVs that have already been processed
            all_cvs = [cv for cv in all_cvs if cv not in previously_extracted_cvs]

        # Print the number of CVs that are left to be processed
        print(f'Number of CVs to be processed: {len(all_cvs)}')
        print(f'Debug: Files to process: {all_cvs}')

        # Return the list of CVs to be processed
        return all_cvs

    # Method to extract text from a PDF file using OCR
    def _extract_text_from_pdf(self, pdf_path):
        print(f"Extracting text from file: {pdf_path}")
        try:
            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=300)  # Higher DPI for better OCR
            text = ""
            
            # Process each page
            for i, image in enumerate(images):
                # Run OCR on the image
                page_text = pytesseract.image_to_string(image)
                if page_text:  # Ensure it’s not None
                    text += page_text + "\n"
                print(f"Debug: Extracted text (first 200 chars) from page {i+1} of {os.path.basename(pdf_path)}: {page_text[:200] if page_text else 'No text extracted'}...")
            
            # Return text if it exists, otherwise empty string
            return text if text.strip() else ""
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {str(e)}")
            return ""

    # Define a method that reads PDF content from a directory
    def _read_pdfs_content_from_directory(self, directory_path):
        # Initialize a dictionary to hold the filenames and contents of the CVs
        data = {'CV_Filename': [], 'CV_Content': []}
        
        # Read all the new files in the directory
        all_cvs = self._read_new_directory_files()
        
        # For each file in the directory
        for filename in tqdm(all_cvs, desc='CVs'):
            # If the file is a PDF
            if filename.endswith('.pdf'):
                # Construct the full file path
                file_path = os.path.join(directory_path, filename)
                try:
                    # Extract the text content from the PDF
                    content = self._extract_text_from_pdf(file_path)
                    # Add the filename to the dictionary
                    data['CV_Filename'].append(filename)
                    # Add the content to the dictionary
                    data['CV_Content'].append(content)
                except Exception as e:
                    # Print the exception if there is an error in reading the file
                    print(f"Error reading file {filename}: {e}")
                    data['CV_Filename'].append(filename)
                    data['CV_Content'].append("")  # Ensure no None values
        # Return the data as a DataFrame
        return pd.DataFrame(data)

    # Define a method that reads and cleans CVs
    def read_cv(self):
        # Print a message indicating the start of the CV extraction process
        print('---- Excecuting CVs Content Extraction Process ----')
        
        # Read the PDFs from the directory and store their content in a DataFrame
        df = self._read_pdfs_content_from_directory(self.cvs_directory_path)
        
        # Print a message indicating the start of the CV content cleaning process
        print('Cleaning CVs Content...')
        # Only apply .str.replace if CV_Content has string values
        if not df['CV_Content'].empty and df['CV_Content'].dtype == object:
            df['CV_Content'] = df['CV_Content'].fillna("").str.replace(r"\n(?:\s*)", "\n", regex=True)

        # Print a message indicating the end of the CV extraction process
        print('CVs Content Extraction Process Completed!')
        print('----------------------------------------------')
        # Return the DataFrame
        return df


# Optional: If running this file directly, add a test
if __name__ == "__main__":
    reader = CVsReader("../CVs")
    df = reader.read_cv()
    print(df)