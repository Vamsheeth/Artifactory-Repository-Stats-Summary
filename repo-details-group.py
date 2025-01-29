import requests
import pandas as pd
import matplotlib.pyplot as plt
import os
import argparse
from dotenv import load_dotenv
from datetime import datetime

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables from a .env file, if present
load_dotenv()


# Function to handle argument parsing and environment variable fallbacks
def get_configuration():
    parser = argparse.ArgumentParser(description="Artifactory Configuration")

    # Define command-line arguments with default values from environment or .env
    parser.add_argument('--artifactory-url', type=str, default=os.getenv("ARTIFACTORY_URL"),
                        help="Artifactory URL (default: from environment variable or .env file)")
    parser.add_argument('--username', type=str, default=os.getenv("USERNAME"),
                        help="Username for Artifactory (default: from environment variable or .env file)")
    parser.add_argument('--password', type=str, default=os.getenv("PASSWORD"),
                        help="Password for Artifactory (default: from environment variable or .env file)")

    # Handle case where REPOSITORY_NAMES might be None in the environment variable
    repository_names = os.getenv("REPOSITORY_NAMES")
    if repository_names is None:
        repository_names = []
    else:
        repository_names = repository_names.split(',')

    parser.add_argument('--repository-names', type=str, nargs='+', default=repository_names,
                        help="List of Artifactory Repository Names (default: from environment variable or .env file)")

    # Parse command-line arguments
    args = parser.parse_args()

    # Ensure required arguments are set either from the command-line, environment, or .env
    if not args.artifactory_url or not args.username or not args.password or not args.repository_names:
        raise ValueError("One or more required values are missing: ARTIFACTORY_URL, USERNAME, PASSWORD, REPOSITORY_NAMES")

    return args.artifactory_url, args.username, args.password, args.repository_names


# Function to execute the AQL query
def execute_aql_query(aql_query, artifactory_url, username, password):
    url = f"{artifactory_url}/api/search/aql"
    headers = {"Content-Type": "text/plain"}

    try:
        response = requests.post(url, auth=(username, password), data=aql_query, headers=headers, verify=False)
        response.raise_for_status()  # Raise HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error executing AQL query: {e}")
        return None


def generate_aql_query(repository_name):
    # Fixed AQL query without trailing comma
    return f'''
items.find({{
    "repo": "{repository_name}"
}}).include("name", "repo", "path", "type", "size", "created", "created_by", "modified", "modified_by", "updated", "stat")
'''


# Function to process the results from AQL
def process_results(result):
    # Check the structure of the response
    # print(result)  # This will help to see if 'created' exists

    processed_results = [
        {
            "repo": item.get("repo"),
            "path": item.get("path"),
            "name": item.get("name"),
            "type": item.get("type"),
            "size": item.get("size"),
            "created": item.get("created"),  # Use .get() to avoid KeyError
            "created_by": item.get("created_by"),
            "modified": item.get("modified"),
            "modified_by": item.get("modified_by"),
            "updated": item.get("updated"),
            "downloads": item.get("stats", [{}])[0].get("downloads", 0),
            "downloaded_by": item.get("stats", [{}])[0].get("downloaded_by", "N/A"),
            "last_downloaded": item.get("stats", [{}])[0].get("downloaded", "N/A")
        }
        for item in result.get("results", [])
    ]
    
    # Create DataFrame and convert 'created' to datetime
    df = pd.DataFrame(processed_results)
    
    # Check if 'created' column exists and is not empty
    if 'created' in df.columns:
        df['created'] = pd.to_datetime(df['created'], errors='coerce')  # 'coerce' will turn invalid parsing to NaT
    else:
        print("Warning: 'created' column is missing.")
        
    return df


# Function to convert byte size to GB
def bytes_to_gb(bytes_size):
    return round(bytes_size / (1024 ** 3), 2)  # Convert bytes to GB and round to 2 decimal places

# Function to remove timezone information from the DataFrame
def remove_timezone(df):
    df['created'] = pd.to_datetime(df['created'], errors='coerce')
    df['modified'] = pd.to_datetime(df['modified'], errors='coerce')
    
    # Remove timezone info if present
    if df['created'].dt.tz is not None:
        df['created'] = df['created'].dt.tz_localize(None)
    
    if df['modified'].dt.tz is not None:
        df['modified'] = df['modified'].dt.tz_localize(None)
    
    return df

# Function to generate the summary and write data to Excel
def write_to_excel(df, repository_name):
    # Extract year and month for analysis
    df['year'] = df['created'].dt.year
    df['month'] = df['created'].dt.month
    df['size_in_gb'] = df['size'].apply(bytes_to_gb)

    # **Fix for Download Range**: Grouping by actual downloads
    download_ranges = pd.cut(df['downloads'], bins=[0, 10, 20, 30, 40, 50, float('inf')],
                             labels=['1-10', '11-20', '21-30', '31-40', '41-50', '50+'])
    download_summary = df.groupby(download_ranges)['downloads'].count().reset_index(name="Count")

    # Group by year and calculate the number of artifacts and total space occupied
    yearly_summary = df.groupby('year').agg(
        num_not_downloaded=('name', 'count'),
        total_space_occupied=('size_in_gb', 'sum')
    ).reset_index()

    # **Fix for Monthly Upload Count**: Breakdown by month and year
    df['month_year'] = df['created'].dt.strftime('%b %Y')
    monthly_uploads = df.groupby('month_year').agg(
        monthly_upload_count=('name', 'count')
    ).reset_index()

    # Group by user for uploads count
    uploads_by_user = df['created_by'].value_counts().reset_index()
    uploads_by_user.columns = ['User', 'Upload Count']

    # Generate dynamic filename based on repository name and timestamp
    timestamp = datetime.now().strftime('%Y%b%dT%H%MHZ')
    filename = f"{repository_name}-{timestamp}-stats.xlsx"

    # Write to Excel with formatting
    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)

        # Summary sheet
        summary_data = {
            "Zero Downloads": len(df[df["downloads"] == 0]),
            "Yearly Uploads": df["created"].dt.year.value_counts().to_dict(),
            "Uploads By User": df["created_by"].value_counts().to_dict(),
        }
        summary_df = pd.DataFrame.from_dict(summary_data, orient="index", columns=["Count"])
        summary_df.to_excel(writer, sheet_name="Summary")

        # Download Range Summary (1-10, 11-20, etc.)
        download_summary.to_excel(writer, sheet_name="Summary", startrow=summary_df.shape[0] + 2, index=False)

        # Yearly summary
        yearly_summary.to_excel(writer, sheet_name="Summary", startrow=summary_df.shape[0] + download_summary.shape[0] + 4, index=False)

        # Monthly Uploads breakdown
        monthly_uploads.to_excel(writer, sheet_name="Summary", startrow=summary_df.shape[0] + download_summary.shape[0] + yearly_summary.shape[0] + 6, index=False)

        # Uploads By User table
        uploads_by_user.to_excel(writer, sheet_name="Summary", startrow=summary_df.shape[0] + download_summary.shape[0] + yearly_summary.shape[0] + monthly_uploads.shape[0] + 8, index=False)

        # Create graphs
        workbook = writer.book
        worksheet = workbook.add_worksheet("Graphs")
        writer.sheets["Graphs"] = worksheet

        # Ensure the directory exists for saving images
        if not os.path.exists("images"):
            os.makedirs("images")

        # Graph 1: Yearly Uploads (Bar Chart)
        plt.figure(figsize=(10, 6))
        yearly_uploads = df["created"].dt.year.value_counts().sort_index()
        yearly_uploads.plot(kind="bar", title="Yearly Uploads", color="skyblue")
        plt.tight_layout()
        yearly_uploads_img_path = "images/yearly_uploads.png"
        plt.savefig(yearly_uploads_img_path)
        plt.close()
        worksheet.insert_image("B2", yearly_uploads_img_path)

        # Graph 2: Uploads by User (Pie Chart)
        plt.figure(figsize=(8, 8))
        uploads_by_user.set_index('User').plot(kind="pie", y='Upload Count', title="Uploads by User", autopct="%1.1f%%", colors=plt.cm.Paired.colors, legend=False)
        plt.tight_layout()
        uploads_by_user_img_path = "images/uploads_by_user.png"
        plt.savefig(uploads_by_user_img_path)
        plt.close()
        worksheet.insert_image("B20", uploads_by_user_img_path)

        # Graph 3: Monthly Uploads Breakdown (Bar Chart)
        plt.figure(figsize=(10, 6))
        monthly_uploads_pivot = monthly_uploads.set_index('month_year').sort_index()
        monthly_uploads_pivot.plot(kind="bar", title="Monthly Uploads Breakdown", color="lightgreen")
        plt.tight_layout()
        monthly_uploads_img_path = "images/monthly_uploads.png"
        plt.savefig(monthly_uploads_img_path)
        plt.close()
        worksheet.insert_image("B40", monthly_uploads_img_path)

    print(f"Excel file '{filename}' created successfully!")

# Main execution
def main():
    artifactory_url, username, password, repository_names = get_configuration()

    for repository_name in repository_names:
        print(f"Processing repository: {repository_name}")

        aql_query = generate_aql_query(repository_name)
        print("Generated AQL query:", aql_query)

        result = execute_aql_query(aql_query, artifactory_url, username, password)

        if result:
            df = process_results(result)
            df = remove_timezone(df)  # Remove timezone info
            write_to_excel(df, repository_name)
        else:
            print(f"Failed to retrieve data for repository {repository_name}.")

if __name__ == "__main__":
    main()
