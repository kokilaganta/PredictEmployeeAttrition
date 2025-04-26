import pickle
import pandas as pd

with open("final_prediction.pkl", "rb") as f:
    model = pickle.load(f)

# Loop through combinations to see if any predict LEAVE
for sat in [0.1, 0.2, 0.3]:
    for eval in [0.2, 0.3, 0.4]:
        for proj in [2, 3]:
            test_input = pd.DataFrame([{
                'satisfaction_level': sat,
                'last_evaluation': eval,
                'number_project': proj,
                'average_monthly_hours': 90,
                'time_spend_company': 5,
                'work_accident': 0,
                'promotion_last_5years': 0,
                'Department': 4,
                'salary': 0
            }])

            test_input.columns = model.feature_names_in_
            pred = model.predict(test_input)[0]

            if pred == 1:
                print("FOUND LEAVE:")
                print(test_input)
                exit()

print("No case predicted leave")
