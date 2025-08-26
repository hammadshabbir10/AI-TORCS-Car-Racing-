import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.neural_network import MLPRegressor
import os
import joblib
from driver import Driver

def load_and_preprocess_data():
    # Create models directory if it doesn't exist
    os.makedirs('models', exist_ok=True)
    
    # Load the dataset
    print("Loading sensor data...")
    data = pd.read_csv('sensor_data/sensor_data.csv')
    
    # Print available columns
    print("\nAvailable columns in the dataset:")
    print(data.columns.tolist())
    
    # Define features based on available columns
    features = []
    # Add track sensors
    for i in range(19):
        if f'track_{i}' in data.columns:
            features.append(f'track_{i}')
    
    # Add other features
    additional_features = ['trackPos', 'angle', 'speedX', 'speedY', 'speedZ', 'rpm', 'gear']
    for feature in additional_features:
        if feature in data.columns:
            features.append(feature)
    
    print("\nUsing features:", features)
    
    # Define target variables
    target = ['accel', 'brake', 'steer', 'gear']
    
    # Verify target columns exist
    missing_targets = [t for t in target if t not in data.columns]
    if missing_targets:
        raise ValueError(f"Missing target columns: {missing_targets}")
    
    # Split features and target
    X = data[features]
    y = data[target]
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Scale the features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Save the scaler
    joblib.dump(scaler, 'models/nn_scaler.pkl')
    
    return X_train_scaled, X_test_scaled, y_train, y_test

def create_model():
    model = MLPRegressor(
        hidden_layer_sizes=(256, 128, 64),
        activation='relu',
        solver='adam',
        alpha=0.0001,  # L2 penalty
        batch_size=32,
        learning_rate='adaptive',
        max_iter=1000,
        early_stopping=True,
        validation_fraction=0.1,
        n_iter_no_change=10,
        random_state=42
    )
    return model

def train_model(X_train, y_train, X_test, y_test):
    print("Training Neural Network model...")
    
    # Create model
    model = create_model()
    
    # Train model
    model.fit(X_train, y_train)
    
    return model

def evaluate_model(model, X_test, y_test):
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    
    # Calculate metrics for each target
    metrics = {}
    for i, target_name in enumerate(y_test.columns):
        mse = mean_squared_error(y_test.iloc[:, i], y_pred[:, i])
        r2 = r2_score(y_test.iloc[:, i], y_pred[:, i])
        metrics[target_name] = {'MSE': mse, 'R2': r2}
        print(f"\nMetrics for {target_name}:")
        print(f"Mean Squared Error: {mse:.4f}")
        print(f"R2 Score: {r2:.4f}")
    
    return metrics

class NNDriver(Driver):
    def __init__(self, stage, model_path="models/nn_model.pkl", scaler_path="models/nn_scaler.pkl"):
        super().__init__(stage)
        self.model = self._load_model(model_path)
        self.scaler = self._load_scaler(scaler_path)
        self.last_gear = 1  # Start in first gear
        self.initialized = False

    def _load_model(self, model_path):
        try:
            return joblib.load(model_path)
        except Exception as e:
            print(f"Error loading model: {e}")
            return None

    def _load_scaler(self, scaler_path):
        try:
            return joblib.load(scaler_path)
        except Exception as e:
            print(f"Error loading scaler: {e}")
            return None

    def parse_sensors(self, msg):
        """Parse the sensor message from TORCS"""
        state = {}
        parts = msg.strip('()').split(')(')
        
        for part in parts:
            if part.startswith('angle'):
                state['angle'] = float(part.split(' ')[1])
            elif part.startswith('track '):
                track_values = part.split(' ')[1:]
                state['track'] = [float(x) for x in track_values]
            elif part.startswith('trackPos'):
                state['trackPos'] = float(part.split(' ')[1])
            elif part.startswith('speedX'):
                state['speedX'] = float(part.split(' ')[1])
            elif part.startswith('speedY'):
                state['speedY'] = float(part.split(' ')[1])
            elif part.startswith('speedZ'):
                state['speedZ'] = float(part.split(' ')[1])
            elif part.startswith('rpm'):
                state['rpm'] = float(part.split(' ')[1])
            elif part.startswith('gear'):
                state['gear'] = int(part.split(' ')[1])
        
        return state

    def _prepare_state(self, state):
        # Extract features in the same order as training
        features = []
        
        # Add track sensors (track_0 to track_18)
        for i in range(19):
            if i < len(state['track']):
                features.append(state['track'][i])
            else:
                features.append(0.0)
        
        # Add other features in the same order as training
        features.extend([
            state.get('trackPos', 0.0),
            state.get('angle', 0.0),
            state.get('speedX', 0.0),
            state.get('speedY', 0.0),
            state.get('speedZ', 0.0),
            state.get('rpm', 0.0),
            state.get('gear', 1)
        ])
        
        # Convert to numpy array and reshape
        features = np.array(features).reshape(1, -1)
        
        # Scale features
        if self.scaler is not None:
            features = self.scaler.transform(features)
        
        return features

    def drive(self, msg):
        if self.model is None or self.scaler is None:
            return '(accel 0) (brake 0) (steer 0) (gear 1)'
        
        # Parse the message
        state = self.parse_sensors(msg)
        
        # Initialize gear if not done
        if not self.initialized:
            self.last_gear = 1
            self.initialized = True
            return f'(accel 0.5) (brake 0) (steer 0) (gear 1)'
        
        # Prepare state for prediction
        features = self._prepare_state(state)
        
        # Get prediction
        prediction = self.model.predict(features)[0]
        
        # Extract control values in the same order as training targets
        acceleration = float(prediction[0])  # accel
        braking = float(prediction[1])      # brake
        steering = float(prediction[2])     # steer
        gear = int(prediction[3])           # gear
        
        # Ensure gear is within valid range
        gear = max(1, min(6, gear))
        
        # Create control string
        return f'(accel {acceleration:.3f}) (brake {braking:.3f}) (steer {steering:.3f}) (gear {gear})'

def main():
    # Load and preprocess data
    X_train, X_test, y_train, y_test = load_and_preprocess_data()
    
    # Train model
    model = train_model(X_train, y_train, X_test, y_test)
    
    # Evaluate model
    metrics = evaluate_model(model, X_test, y_test)
    
    # Save model
    joblib.dump(model, 'models/nn_model.pkl')
    
    print("\nTraining complete!")

if __name__ == "__main__":
    main() 