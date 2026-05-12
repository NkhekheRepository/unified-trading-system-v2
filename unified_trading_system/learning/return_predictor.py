"""
Return Prediction Model for Trading System
Implements deep learning models for predicting future returns from microstructure features
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime
import os
import json

logger = logging.getLogger(__name__)

class TemporalConvNet(nn.Module):
    """
    Temporal Convolutional Network for financial time series prediction
    """
    
    def __init__(self, input_size: int, num_channels: List[int], kernel_size: int = 2, dropout: float = 0.2):
        super(TemporalConvNet, self).__init__()
        layers = []
        num_levels = len(num_channels)
        for i in range(num_levels):
            dilation_size = 2 ** i
            in_channels = input_size if i == 0 else num_channels[i-1]
            out_channels = num_channels[i]
            # Use 'same' padding to maintain sequence length
            padding = kernel_size - 1
            layers += [TemporalBlock(in_channels, out_channels, kernel_size, stride=1, 
                                   dilation=dilation_size, padding=padding, 
                                   dropout=dropout)]
        
        self.network = nn.Sequential(*layers)
        self.linear = nn.Linear(num_channels[-1], 1)  # Output single return prediction
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)
        # Convert to (batch_size, input_size, sequence_length) for Conv1d
        x = x.transpose(1, 2)
        y = self.network(x)
        # Take the last time step
        y = y[:, :, -1]
        # Project to output
        return self.linear(y)

class TemporalBlock(nn.Module):
    """
    Building block for Temporal Convolutional Network
    """
    
    def __init__(self, n_inputs: int, n_outputs: int, kernel_size: int, stride: int, 
                 dilation: int, padding: int, dropout: float = 0.2):
        super(TemporalBlock, self).__init__()
        self.conv1 = nn.Conv1d(n_inputs, n_outputs, kernel_size, stride=stride, 
                              padding=padding, dilation=dilation)
        self.ch1 = nn.BatchNorm1d(n_outputs)
        self.net1 = nn.Sequential(self.conv1, self.ch1, nn.Dropout(dropout))
        
        self.conv2 = nn.Conv1d(n_outputs, n_outputs, kernel_size, stride=stride, 
                              padding=padding, dilation=dilation)
        self.ch2 = nn.BatchNorm1d(n_outputs)
        self.net2 = nn.Sequential(self.conv2, self.ch2, nn.Dropout(dropout))
        
        self.downsample = nn.Conv1d(n_inputs, n_outputs, 1) if n_inputs != n_outputs else None
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        out = self.net1(x)
        out = self.net2(out)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(self.dropout(out + res))

class TransformerEncoder(nn.Module):
    """
    Transformer Encoder for sequence modeling
    """
    
    def __init__(self, input_size: int, d_model: int = 64, nhead: int = 8, 
                 num_layers: int = 4, dim_feedforward: int = 256, dropout: float = 0.1):
        super(TransformerEncoder, self).__init__()
        self.input_projection = nn.Linear(input_size, d_model)
        encoder_layer = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward, dropout)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        self.output_projection = nn.Linear(d_model, 1)
        self.d_model = d_model
        
    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)
        x = self.input_projection(x)  # (batch_size, sequence_length, d_model)
        # Transformer expects (sequence_length, batch_size, d_model)
        x = x.transpose(0, 1)
        x = self.transformer_encoder(x)
        # Take the last time step
        x = x[-1, :, :]  # (batch_size, d_model)
        x = self.output_projection(x)  # (batch_size, 1)
        return x

class ReturnPredictor(nn.Module):
    """
    Main return prediction model that combines multiple architectures
    """
    
    def __init__(self, input_size: int, sequence_length: int = 20, 
                 model_type: str = "lstm", **kwargs):
        super(ReturnPredictor, self).__init__()
        self.input_size = input_size
        self.sequence_length = sequence_length
        self.model_type = model_type
        self.hidden_size = kwargs.get('hidden_size', 32)
        
        if model_type == "tcn":
            # Simple MLP for single feature vector prediction
            self.fc1 = nn.Linear(input_size * sequence_length, 32)
            self.fc2 = nn.Linear(32, 16)
            self.fc3 = nn.Linear(16, 1)
            self.dropout = nn.Dropout(kwargs.get('dropout', 0.2))
        elif model_type == "transformer":
            self.model = TransformerEncoder(
                input_size=input_size,
                d_model=kwargs.get('d_model', 64),
                nhead=kwargs.get('nhead', 8),
                num_layers=kwargs.get('num_layers', 4),
                dim_feedforward=kwargs.get('dim_feedforward', 256),
                dropout=kwargs.get('dropout', 0.1)
            )
        elif model_type == "lstm":
            self.model = nn.LSTM(
                input_size=input_size,
                hidden_size=self.hidden_size,
                num_layers=kwargs.get('num_layers', 2),
                dropout=kwargs.get('dropout', 0.2),
                batch_first=True
            )
            self.output_projection = nn.Linear(self.hidden_size, 1)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
            
        # Uncertainty estimation head - takes predictions as input
        self.uncertainty_head = nn.Linear(1, 1)
        
        # For LSTM, also need output projection
        if model_type == "lstm":
            self.output_projection = nn.Linear(kwargs.get('hidden_size', 32), 1)
        
    def forward(self, x, return_uncertainty: bool = False):
        """
        Forward pass through the model
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size)
            return_uncertainty: Whether to return uncertainty estimates
            
        Returns:
            If return_uncertainty=False: predictions tensor of shape (batch_size, 1)
            If return_uncertainty=True: tuple of (predictions, uncertainty)
        """
        if self.model_type == "lstm":
            # LSTM returns (output, (hidden, cell))
            lstm_out, _ = self.model(x)
            # Take the last time step output
            features = lstm_out[:, -1, :]
            predictions = self.output_projection(features)
        elif self.model_type == "tcn":
            # Simple MLP forward - flatten input
            x_flat = x.view(x.size(0), -1)  # (batch, seq_len * input_size)
            x_flat = torch.relu(self.fc1(x_flat))
            x_flat = self.dropout(x_flat)
            x_flat = torch.relu(self.fc2(x_flat))
            predictions = self.fc3(x_flat)
        else:
            predictions = self.model(x)
            
        if return_uncertainty:
            # Use the predictions for uncertainty estimation
            uncertainty = self.uncertainty_head(predictions)
            return predictions, uncertainty
        else:
            return predictions
    
    def get_uncertainty_features(self, x):
        """Get features for uncertainty estimation"""
        if self.model_type == "lstm":
            lstm_out, _ = self.model(x)
            features = lstm_out[:, -1, :]
        else:
            # Get intermediate features from model
            x_transposed = x.transpose(1, 2)
            features = self.model.network(x_transposed)
            features = features[:, :, -1]
        return features

class ReturnPredictorWrapper:
    """
    Wrapper class for the ReturnPredictor model that handles training, 
    inference, and model management
    """
    
    def __init__(self, input_size: int, sequence_length: int = 20, 
                 model_type: str = "tcn", device: str = None, 
                 learning_rate: float = 0.001):
        self.input_size = input_size
        self.sequence_length = sequence_length
        self.model_type = model_type
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.learning_rate = learning_rate
        
        # Initialize model
        self.model = ReturnPredictor(
            input_size=input_size,
            sequence_length=sequence_length,
            model_type=model_type
        ).to(self.device)
        
        # Initialize optimizer
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        
        # Loss function
        self.criterion = nn.MSELoss()
        
        # Training history
        self.training_losses = []
        self.validation_losses = []
        
        logger.info(f"Initialized {model_type.upper()} return predictor on {self.device}")
        
    def prepare_sequence(self, feature_vector: np.ndarray) -> torch.Tensor:
        """
        Convert feature vector to tensor for model input
        """
        # For now, we'll replicate the feature vector to create a sequence
        # In practice, this would use actual historical sequences
        sequence = np.tile(feature_vector, (self.sequence_length, 1))
        sequence = sequence.astype(np.float32)
        tensor = torch.FloatTensor(sequence).unsqueeze(0)  # Add batch dimension
        return tensor.to(self.device)
    
    def predict_return(self, feature_vector: np.ndarray, 
                      return_uncertainty: bool = False) -> Tuple[float, Optional[float]]:
        """
        Predict return from feature vector
        
        Args:
            feature_vector: Input features as numpy array
            return_uncertainty: Whether to return uncertainty estimate
            
        Returns:
            prediction: Predicted return
            uncertainty: Uncertainty estimate (if requested)
        """
        self.model.eval()
        with torch.no_grad():
            tensor_input = self.prepare_sequence(feature_vector)
            if return_uncertainty:
                prediction, uncertainty = self.model(tensor_input, return_uncertainty=True)
                return prediction.item(), uncertainty.item()
            else:
                prediction = self.model(tensor_input, return_uncertainty=False)
                return prediction.item(), None
    
    def train_batch(self, sequences: torch.Tensor, targets: torch.Tensor) -> float:
        """
        Train model on a batch of data
        
        Args:
            sequences: Input sequences of shape (batch_size, sequence_length, input_size)
            targets: Target returns of shape (batch_size, 1)
            
        Returns:
            loss: Training loss for the batch
        """
        self.model.train()
        self.optimizer.zero_grad()
        
        # Forward pass
        predictions = self.model(sequences)
        loss = self.criterion(predictions, targets)
        
        # Backward pass
        loss.backward()
        self.optimizer.step()
        
        loss_value = loss.item()
        self.training_losses.append(loss_value)
        
        return loss_value
    
    def validate_batch(self, sequences: torch.Tensor, targets: torch.Tensor) -> float:
        """
        Validate model on a batch of data
        
        Args:
            sequences: Input sequences of shape (batch_size, sequence_length, input_size)
            targets: Target returns of shape (batch_size, 1)
            
        Returns:
            loss: Validation loss for the batch
        """
        self.model.eval()
        with torch.no_grad():
            predictions = self.model(sequences)
            loss = self.criterion(predictions, targets)
            loss_value = loss.item()
            self.validation_losses.append(loss_value)
            return loss_value
    
    def save_model(self, filepath: str):
        """
        Save model to file
        """
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'input_size': self.input_size,
            'sequence_length': self.sequence_length,
            'model_type': self.model_type,
            'training_losses': self.training_losses,
            'validation_losses': self.validation_losses,
        }, filepath)
        logger.info(f"Model saved to {filepath}")
        
    def load_model(self, filepath: str):
        """
        Load model from file
        """
        if os.path.exists(filepath):
            checkpoint = torch.load(filepath, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            self.input_size = checkpoint['input_size']
            self.sequence_length = checkpoint['sequence_length']
            self.model_type = checkpoint['model_type']
            self.training_losses = checkpoint.get('training_losses', [])
            self.validation_losses = checkpoint.get('validation_losses', [])
            logger.info(f"Model loaded from {filepath}")
        else:
            logger.warning(f"Model file {filepath} not found")
            
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the model
        """
        return {
            'model_type': self.model_type,
            'input_size': self.input_size,
            'sequence_length': self.sequence_length,
            'device': self.device,
            'training_samples': len(self.training_losses),
            'validation_samples': len(self.validation_losses),
            'latest_training_loss': self.training_losses[-1] if self.training_losses else None,
            'latest_validation_loss': self.validation_losses[-1] if self.validation_losses else None
        }

class EnsembleReturnPredictor:
    """
    Ensemble of multiple return prediction models for improved robustness
    """
    
    def __init__(self, input_size: int, sequence_length: int = 20):
        self.input_size = input_size
        self.sequence_length = sequence_length
        self.models = {}
        self.weights = {}
        
        # Initialize different model types
        model_configs = [
            {'type': 'tcn', 'name': 'tcn_small'},
            {'type': 'tcn', 'name': 'tcn_large', 'params': {'num_channels': [128, 128, 128]}},
            {'type': 'transformer', 'name': 'transformer_base'},
            {'type': 'lstm', 'name': 'lstm_base'}
        ]
        
        for config in model_configs:
            model_type = config['type']
            name = config['name']
            params = config.get('params', {})
            
            self.models[name] = ReturnPredictorWrapper(
                input_size=input_size,
                sequence_length=sequence_length,
                model_type=model_type,
                **params
            )
            # Initialize equal weights
            self.weights[name] = 1.0 / len(model_configs)
            
        logger.info(f"Initialized ensemble with {len(self.models)} models")
        
    def predict_return(self, feature_vector: np.ndarray, 
                      return_uncertainty: bool = False) -> Tuple[float, Optional[float]]:
        """
        Make prediction using weighted ensemble
        """
        predictions = []
        uncertainties = [] if return_uncertainty else None
        total_weight = 0.0
        
        for name, model in self.models.items():
            weight = self.weights[name]
            pred, unc = model.predict_return(feature_vector, return_uncertainty)
            
            predictions.append(pred * weight)
            total_weight += weight
            
            if return_uncertainty and unc is not None:
                uncertainties.append((unc, weight))
                
        # Normalize by total weight
        final_prediction = sum(predictions) / total_weight if total_weight > 0 else 0.0
        
        if return_uncertainty and uncertainties:
            # Weighted average of uncertainties
            weighted_uncertainty = sum(u * w for u, w in uncertainties) / total_weight if total_weight > 0 else 0.0
            return final_prediction, weighted_uncertainty
        else:
            return final_prediction, None
    
    def update_weights(self, performance_scores: Dict[str, float]):
        """
        Update model weights based on recent performance
        """
        total_score = sum(performance_scores.values())
        if total_score > 0:
            for name in self.weights:
                self.weights[name] = performance_scores.get(name, 0.0) / total_score
        else:
            # Equal weights if no performance data
            equal_weight = 1.0 / len(self.models)
            for name in self.weights:
                self.weights[name] = equal_weight
                
        logger.info(f"Updated ensemble weights: {self.weights}")
        
    def save_all_models(self, base_path: str):
        """
        Save all models in the ensemble
        """
        for name, model in self.models.items():
            filepath = f"{base_path}_{name}.pt"
            model.save_model(filepath)
            
    def load_all_models(self, base_path: str):
        """
        Load all models in the ensemble
        """
        for name, model in self.models.items():
            filepath = f"{base_path}_{name}.pt"
            model.load_model(filepath)

def create_return_predictor(input_size: int, **kwargs) -> ReturnPredictorWrapper:
    """
    Factory function to create a return predictor
    """
    model_type = kwargs.get('model_type', 'lstm')
    # Remove model_type from kwargs to avoid duplicate parameter
    kwargs_copy = kwargs.copy()
    kwargs_copy.pop('model_type', None)
    return ReturnPredictorWrapper(
        input_size=input_size,
        model_type=model_type,
        **kwargs_copy
    )

def create_ensemble_predictor(input_size: int) -> EnsembleReturnPredictor:
    """
    Factory function to create an ensemble predictor
    """
    return EnsembleReturnPredictor(input_size=input_size)