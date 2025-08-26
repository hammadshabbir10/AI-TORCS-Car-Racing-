import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# Load the CSV file
data = pd.read_csv('logs/telemetry_data.csv')

# 1. Remove any rows with missing values
print("Initial data size:", data.shape)
data.dropna(inplace=True)
print("After removing missing values:", data.shape)

# 2. Convert data types (ensure all numerical columns are float)
numeric_columns = ['distance', 'angle', 'trackPos', 'speedX', 'rpm', 'gear', 'steer', 'accel', 'brake']
data[numeric_columns] = data[numeric_columns].astype(float)

# 3. Normalize/Scale Data
scaler = MinMaxScaler()
data[numeric_columns] = scaler.fit_transform(data[numeric_columns])

# 4. One-Hot Encode Track and Car columns
data = pd.get_dummies(data, columns=['track', 'car'])

# 5. Feature Engineering - Calculate Changes
data['speed_diff'] = data['speedX'].diff().fillna(0)
data['steer_diff'] = data['steer'].diff().fillna(0)
data['accel_diff'] = data['accel'].diff().fillna(0)

# 6. Save Cleaned Data
data.to_csv('logs/cleaned_telemetry_data.csv', index=False)
print("Data cleaning and preprocessing complete. Cleaned data saved.")

