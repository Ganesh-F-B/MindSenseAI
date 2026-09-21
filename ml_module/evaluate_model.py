print("SCRIPT STARTED")
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report

# Load dataset
df = pd.read_csv("C:/Users/ganes/OneDrive/Desktop/MindSenseAI/ml_module/mental_heath_feature_engineered.csv")
# Features and labels
X = df["text"]
y = df["label"]

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.3,
    random_state=42
)

# NLP + ML Pipeline
model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", MultinomialNB())
])

# Train model
model.fit(X_train, y_train)

# Predictions
predictions = model.predict(X_test)

# Accuracy
accuracy = accuracy_score(y_test, predictions)

print("\n==============================")
print("MODEL ACCURACY")
print("==============================")
print(f"Accuracy: {accuracy * 100:.2f}%")

print("\n==============================")
print("CLASSIFICATION REPORT")
print("==============================")
print(classification_report(y_test, predictions))

# Real-time testing
print("\n==============================")
print("LIVE TEST")
print("==============================")

while True:
    user_input = input("\nEnter message (or type quit): ")

    if user_input.lower() == "quit":
        break

    prediction = model.predict([user_input])[0]

    print(f"Predicted Mental State: {prediction}")