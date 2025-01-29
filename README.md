# Artifactory Repository Statistics Generator  

This script extracts artifact metadata from JFrog Artifactory using AQL (Artifactory Query Language), processes the data, and generates an Excel report with statistics and visualizations.  

## Features  
- Fetches artifact metadata (name, size, created/modified timestamps, downloads, etc.).  
- Generates an Excel report with multiple sheets, including:  
  - Raw artifact data  
  - Summary statistics  
  - Graphs for yearly uploads, uploads by user, and monthly trends  
- Supports multiple repositories  
- Handles environment variables via `.env` file or command-line arguments  

## Prerequisites  
Ensure you have the following installed:  
- Python 3.x  
- Required Python packages (install via `pip install -r requirements.txt`)  

## Installation  
1. Clone this repository:  
   ```sh
   git clone [https://github.com/your-repo/artifactory-stats.git](https://github.com/Vamsheeth/Artifactory-Repository-Stats-Summary) artifactory-stats
   cd artifactory-stats
   ```  
2. Install dependencies:  
   ```sh
   pip install -r requirements.txt
   ```  
3. Configure environment variables:  
   Create a `.env` file in the project directory with the following:  
   ```env
   ARTIFACTORY_URL=https://your-artifactory-instance.com/artifactory
   USERNAME=your-username
   PASSWORD=your-password
   REPOSITORY_NAMES=repo1,repo2
   ```  

## Usage  

Run the script with command-line arguments or environment variables:  

### Using Environment Variables  
```sh
python script.py
```  

### Using Command-Line Arguments  
```sh
python script.py --artifactory-url "https://your-artifactory.com/artifactory" \
                 --username "your-username" \
                 --password "your-password" \
                 --repository-names repo1 repo2
```  

## Output  
The script generates an Excel file named:  
```
<repository_name>-YYYYMonDDTHHMMHZ-stats.xlsx
```  
It contains:  
1. **Data Sheet** – Raw artifact metadata  
2. **Summary Sheet** – Key statistics  
3. **Graphs Sheet** – Visual charts  

## Notes  
- The script automatically disables SSL warnings for self-signed certificates.  
- Large repositories may take longer to process.  

## License  
This project is licensed under the MIT License.  

## Author  
Vamsheeth Vadlamudi
vamsheethkennady@gmail.com
