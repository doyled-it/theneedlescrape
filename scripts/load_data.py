import numpy as np
import pandas as pd


def load_data():
    data = pd.read_json("data/updated_review_info.jsonl", lines=True)
    return data


df = load_data()
# Flatten the lists
all_values = np.concatenate(df["genres"].values)

# Use pandas to get the counts
value_counts = pd.Series(all_values).value_counts().reset_index()

# Rename the columns
value_counts.columns = ["Value", "Count"]

print(value_counts)
print(df.head())
