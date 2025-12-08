# backend/ai_engine.py
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

# 1. TEACH THE BRAIN (Training Data)
# We teach it patterns: "filename" -> "category"
training_data = [
    # Academic / School
    ("thesis_final.docx", "Academic"),
    ("capstone_proposal.pdf", "Academic"),
    ("homework_math.jpg", "Academic"),
    ("chapter_1_review.docx", "Academic"),
    ("project_documentation.pdf", "Academic"),
    ("enrollment_form.pdf", "Academic"),
    
    # Personal / Photos
    ("IMG_2025.jpg", "Personal"),
    ("family_dinner.png", "Personal"),
    ("boracay_trip.mp4", "Personal"),
    ("screenshot_123.png", "Personal"),
    
    # Work / Other
    ("resume_2025.pdf", "Work"),
    ("budget_plan.xlsx", "Work"),
    ("invoice_september.pdf", "Work")
]

# Split into X (Inputs) and y (Labels)
X_train = [item[0] for item in training_data]
y_train = [item[1] for item in training_data]

# 2. BUILD THE PIPELINE
# CountVectorizer: Turns text into numbers
# MultinomialNB: The AI algorithm (Naive Bayes) that predicts categories
model = make_pipeline(CountVectorizer(), MultinomialNB())

# 3. TRAIN IT
model.fit(X_train, y_train)

def predict_category(filename):
    try:
        # The model predicts the category based on the filename
        prediction = model.predict([filename])
        return prediction[0]
    except:
        return "Other"

# Test it immediately if you run this file
if __name__ == "__main__":
    print(f"Test 'My_Thesis.pdf': {predict_category('My_Thesis.pdf')}")
    print(f"Test 'Party_Photo.jpg': {predict_category('Party_Photo.jpg')}")