# -*- coding: utf-8 -*-
"""text-summarization.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1kYdEddgr4RGkHhqRVHMTxwW2N7wp5F6h
"""

!pip install transformers scikit-learn rouge_score numpy gdown sentencepiece

from transformers import T5ForConditionalGeneration, T5Tokenizer
from torch.utils.data import Dataset, DataLoader
import pandas as pd
from sklearn.model_selection import train_test_split
import torch
from rouge_score import rouge_scorer
import numpy as np
import warnings

warnings.filterwarnings('ignore')

# download data
! gdown 1XG9yHaijUgUgKP9756Rh_Yw1OTHEDxeq

# Define the dataset class
class SummaryDataset(Dataset):
    def __init__(self, data, tokenizer):
        self.data = data
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        dialogue = self.data.iloc[index]["dialogue"]
        summary = self.data.iloc[index]["summary"]

        input_ids = self.tokenizer.encode(str(dialogue), truncation=True, padding="max_length", max_length=512,
                                          return_tensors="pt")
        target_ids = self.tokenizer.encode(str(summary), truncation=True, padding="max_length", max_length=128,
                                           return_tensors="pt")

        return {
            "input_ids": torch.tensor(input_ids, dtype=torch.long),
            "attention_mask": torch.tensor([1] * len(input_ids), dtype=torch.long),
            "target_ids": torch.tensor(target_ids, dtype=torch.long),
            "target_attention_mask": torch.tensor([1] * len(target_ids), dtype=torch.long),
        }

# Load the data from CSV
data = pd.read_csv("validation_vn.csv")  # Update with your CSV file

# Split the data into training and testing sets
train_data, test_data = train_test_split(data, test_size=0.2, random_state=42)

# Create the tokenizer
tokenizer = T5Tokenizer.from_pretrained("NlpHUST/t5-small-vi-summarization")

# Create the datasets
train_dataset = SummaryDataset(train_data, tokenizer)
test_dataset = SummaryDataset(test_data, tokenizer)

# Create the data loaders
batch_size = 4
train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
test_dataloader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)

# Initialize the model
model = T5ForConditionalGeneration.from_pretrained("NlpHUST/t5-small-vi-summarization")

# Initialize the ROUGE scorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Training loop
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

num_epochs = 5

for epoch in range(num_epochs):
    # Training
    model.train()
    total_loss = 0

    for batch in train_dataloader:
        input_ids = batch["input_ids"].to(device).squeeze(1)
        attention_mask = batch["attention_mask"].to(device)
        target_ids = batch["target_ids"].to(device).squeeze(1)
        target_attention_mask = batch["target_attention_mask"].to(device)

        optimizer.zero_grad()

        outputs = model(
            input_ids=input_ids,
            labels=target_ids,
        )

        loss = outputs.loss
        total_loss += loss.item()

        loss.backward()
        optimizer.step()

    average_loss = total_loss / len(train_dataloader)
    print(f"Epoch {epoch + 1}: Training Average Loss = {average_loss:.4f}")

    # Evaluation
    model.eval()
    total_eval_loss = 0
    references = []
    predictions = []

    with torch.no_grad():
        for batch in test_dataloader:
            input_ids = batch["input_ids"].to(device).squeeze(1)
            attention_mask = batch["attention_mask"].to(device)
            target_ids = batch["target_ids"].to(device).squeeze(1)
            target_attention_mask = batch["target_attention_mask"].to(device)

            outputs = model(
                input_ids=input_ids,
                labels=target_ids,
            )

            eval_loss = outputs.loss
            total_eval_loss += eval_loss.item()

            # Convert tensor predictions to text
            predicted_ids = torch.argmax(outputs.logits, dim=-1)
            predicted_texts = tokenizer.batch_decode(predicted_ids, skip_special_tokens=True)
            references += tokenizer.batch_decode(target_ids, skip_special_tokens=True)
            predictions += predicted_texts

    average_eval_loss = total_eval_loss / len(test_dataloader)
    print(f"Epoch {epoch + 1}: Evaluation Average Loss = {average_eval_loss:.4f}")
    # Calculate ROUGE scores
    print(predictions[0])
    rouge_scores = []
    for reference, prediction in zip(references, predictions):
        rouge_scores.append(scorer.score(reference, prediction)['rougeL'].fmeasure)
    print(f"Epoch {epoch + 1}: ROUGE Scores = {np.mean(np.array(rouge_scores))}")