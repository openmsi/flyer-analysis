import numpy as np
import matplotlib.pyplot as plt
import ast

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn import svm
from sklearn.metrics import accuracy_score, matthews_corrcoef
from sklearn.model_selection import GridSearchCV


def main():
    attrs = [
        "radius",
        "tilt",
        "leading_row",
        "center_row",
        "center_column",
    ]

    X = np.load("X_3d.npy")
    X = np.nan_to_num(X, nan=0.0)
    Y = np.loadtxt("Y.txt")

    X_train, X_temp, Y_train, Y_temp = train_test_split(
        X, Y, test_size=0.3, random_state=42
    )
    X_val, X_test, Y_val, Y_test = train_test_split(
        X_temp, Y_temp, test_size=0.5, random_state=42
    )

    # Linear regression
    print("- Linear Regression -")
    for i in range(X_train.shape[-1]):
        print(f"Inferring {attrs[i]}")

        model = LinearRegression()
        model.fit(X_train[:, :, i], Y_train)

        Y_val_pred = model.predict(X_val[:, :, i])

        mse_val = mean_squared_error(Y_val, Y_val_pred)
        r2_val = r2_score(Y_val, Y_val_pred)

        print("Validation MSE:", mse_val)
        print("Validation R^2:", r2_val)

        Y_test_pred = model.predict(X_test[:, :, i])

        mse_test = mean_squared_error(Y_test, Y_test_pred)
        r2_test = r2_score(Y_test, Y_test_pred)

        print("Test MSE:", mse_test)
        print("Test R^2:", r2_test)

        # plt.plot(
        #     X_test[:, :, i],
        #     Y_test_pred,
        #     color="blue",
        #     linewidth=3,
        #     label="Linear regression prediction",
        # )
        # plt.title("Linear Regression: Test Set")
        # plt.xlabel("X")
        # plt.ylabel("Y")
        # plt.legend()
        # # plt.show()
        # plt.savefig(f"{attrs[i]}.png")

    # multivariate regression
    print("- Multivariate analysis -")
    multivar_X = X.reshape(X.shape[0], -1)

    X_train, X_temp, Y_train, Y_temp = train_test_split(
        multivar_X, Y, test_size=0.3, random_state=42
    )
    X_val, X_test, Y_val, Y_test = train_test_split(
        X_temp, Y_temp, test_size=0.5, random_state=42
    )

    model = LinearRegression()
    model.fit(X_train, Y_train)

    Y_val_pred = model.predict(X_val)

    mse_val = mean_squared_error(Y_val, Y_val_pred)
    r2_val = r2_score(Y_val, Y_val_pred)

    print("Validation MSE:", mse_val)
    print("Validation R^2:", r2_val)

    Y_test_pred = model.predict(X_test)

    mse_test = mean_squared_error(Y_test, Y_test_pred)
    r2_test = r2_score(Y_test, Y_test_pred)

    print("Test MSE:", mse_test)
    print("Test R^2:", r2_test)

    # SVR
    print("- SVR analysis - ")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    svr_model = svm.SVC(kernel="linear", C=1.0)
    svr_model.fit(X_train_scaled, Y_train)

    Y_val_pred = svr_model.predict(X_val_scaled)
    val_accuracy = accuracy_score(Y_val, Y_val_pred)

    print(f"Validation Accuracy: {val_accuracy}")

    Y_test_pred = svr_model.predict(X_test_scaled)
    test_accuracy = accuracy_score(Y_test, Y_test_pred)

    print(f"Test Accuracy: {test_accuracy}")

    # SVR with Grid Search
    print("- SVR analysis with Grid Search - ")

    param_grid = {"C": [0.1, 1, 10, 100], "kernel": ["linear", "rbf", "poly"]}

    svr_model = GridSearchCV(svm.SVC(), param_grid, cv=5)

    svr_model.fit(X_train_scaled, Y_train)

    Y_val_pred = svr_model.predict(X_val_scaled)
    val_accuracy = accuracy_score(Y_val, Y_val_pred)
    val_mcc = matthews_corrcoef(Y_val, Y_val_pred)

    print(f"Validation Accuracy: {val_accuracy}")
    print(f"Validation Mathews coefficient: {val_mcc}")

    Y_test_pred = svr_model.predict(X_test_scaled)
    test_accuracy = accuracy_score(Y_test, Y_test_pred)
    test_mcc = matthews_corrcoef(Y_test, Y_test_pred)

    print(f"Test Accuracy: {test_accuracy}")
    print(f"Test Mathews coefficient: {test_mcc}")

    best_params = svr_model.best_params_


if __name__ == "__main__":
    main()
