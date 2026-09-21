print("TRAINING SCRIPT STARTED")

import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

print("LOADING DATASET...")

# Load dataset
df = pd.read_csv("mental_heath_feature_engineered.csv")

# Keep required columns
df = df[["text", "status"]]

# Remove null values
df.dropna(inplace=True)

print("DATASET READY")
print(df.shape)

texts = df["text"]
labels = df["status"]

print("SPLITTING DATASET...")

X_train, X_test, y_train, y_test = train_test_split(
    texts,
    labels,
    test_size=0.2,
    random_state=42
)

print("CREATING TF-IDF FEATURES...")

vectorizer = TfidfVectorizer(
    max_features=20000,
    stop_words='english',
    ngram_range=(1,2),
    min_df=2,
    max_df=0.9,
    sublinear_tf=True
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)

print("TRAINING LOGISTIC REGRESSION MODEL...")

classifier = LogisticRegression(
    max_iter=2000,
    class_weight='balanced'
)

classifier.fit(X_train_tfidf, y_train)

print("MAKING PREDICTIONS...")

predictions = classifier.predict(X_test_tfidf)

accuracy = accuracy_score(y_test, predictions)

print("\n======================")
print("MODEL ACCURACY")
print("======================")
print(f"Accuracy: {accuracy * 100:.2f}%")

print("\n======================")
print("CLASSIFICATION REPORT")
print("======================")
print(classification_report(y_test, predictions))

print("SAVING MODEL...")

joblib.dump(classifier, "mental_health_model.pkl")
joblib.dump(vectorizer, "tfidf_vectorizer.pkl")

print("MODEL SAVED SUCCESSFULLY!")