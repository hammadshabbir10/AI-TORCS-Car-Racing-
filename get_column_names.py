import pandas as pd

# Load the cleaned dataset
cleaned_data_path = 'logs/cleaned_telemetry_data.csv'
cleaned_data = pd.read_csv(cleaned_data_path)

# Get the column names
column_names = cleaned_data.columns.tolist()

# Print the column names
print("Column names in the cleaned dataset:")
for column in column_names:
    print(column)
