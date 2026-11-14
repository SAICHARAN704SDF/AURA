# AURA research report
Status: COMPLETED
Workflow: 982473fb-7ad6-4b9c-99ba-345531f3bba1
Verification: PASS
Reported tokens: 36056

## research
Paper claims: Dataset — composition, size, labels, languages, splits, and collection method were not found in the retrieved excerpts. Preprocessing — concrete cleaning, normalization, tokenization, or feature-engineering steps were not found. Models — the reported leading classifiers are Logistic Regression and a RoBERTa-based transformer; TF-IDF also appears in the hyperparameter table. Results — on the validation set, with metrics ordered Accuracy, Precision, Recall, and F1 Score, Logistic Regression reports 0.91, 0.62, 0.72, and 0.65; RoBERTa reports 0.97, 0.88, 0.77, and 0.81. The paper identifies RoBERTa as its best-performing model. Dashboard — AURORA is presented as a misinformation-classification dashboard at https://misinfo-4.onrender.com/. Limitations — no formal study limitations were found; the paper only warns that free Render hosting may delay loading by about two minutes.

Assessment: The retrieved evidence supports the model names, validation metrics, dashboard URL, and hosting caveat. It is insufficient to assess dataset representativeness, preprocessing reproducibility, test-set performance, statistical uncertainty, baseline fairness, dashboard validation, or generalization claims.

> Logistic Regression and RoBERTa based transformer models on the validation set.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Accuracy
Precision
Recall
F1 Score
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Logistic Regression
0.91
0.62
0.72
0.65
RoBERTa based transformer
0.97
0.88
0.77
0.81
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> TF-IDF
Logistic Regression
RoBERTa
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> We developed a dashboard AURORA from this subtask 3 of misinformation classification model
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

> can be accessed via this link: https://misinfo-4.onrender.com/.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

> this website might cause delay of approx. 2 minutes in showing the webpage.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

Limitation: Only three retrieved chunks were available.
Limitation: Dataset and preprocessing details were not present in those chunks.
Limitation: No final test metrics, uncertainty estimates, or formal limitations section were found.
Limitation: The dashboard was not independently accessed or evaluated.
## analysis
Paper claims (evidence references follow array order): Dataset — retrieved excerpts do not establish size, composition, labels, languages, collection method, or splits. Preprocessing — no cleaning, normalization, tokenization, or feature-engineering procedure is documented in the available evidence. Models — Logistic Regression and a RoBERTa-based transformer were evaluated on a validation set [E1]; TF-IDF is also listed, but its exact role is unclear [E4]. Results — the reported metric order is Accuracy, Precision, Recall, and F1 Score [E2]. Logistic Regression reports 0.91, 0.62, 0.72, and 0.65; RoBERTa reports 0.97, 0.88, 0.77, and 0.81 [E3]. Dashboard — the paper describes AURORA as a misinformation-classification dashboard [E5] and provides a Render URL [E6]. Limitations — no formal research limitations were substantiated by the retrieved excerpts.

Assessment: The available evidence supports only the model names, validation metrics, dashboard purpose, and URL. Missing dataset, preprocessing, evaluation-protocol, test-set, uncertainty, and formal limitation details prevent assessment of representativeness, leakage risk, reproducibility, generalization, or dashboard reliability.

> Logistic Regression and RoBERTa based transformer models on the validation set.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Accuracy
Precision
Recall
F1 Score
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Logistic Regression
0.91
0.62
0.72
0.65
RoBERTa based transformer
0.97
0.88
0.77
0.81
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> TF-IDF
Logistic Regression
RoBERTa
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> We developed a dashboard AURORA from this subtask 3 of misinformation classification model
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

> can be accessed via this link: https://misinfo-4.onrender.com/.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

Limitation: Only three retrieved chunks were available.
Limitation: Dataset and preprocessing details were absent from those chunks.
Limitation: No final test metrics, uncertainty estimates, or formal limitations were found.
Limitation: The dashboard was not independently accessed or evaluated.
## verification
PASS

Limitation: Exact quotes and explicit numeric relations verified; general semantic entailment is not established.
## reporting
Paper claims: Dataset — composition, size, labels, languages, splits, and collection method were not found in the retrieved excerpts. Preprocessing — concrete cleaning, normalization, tokenization, or feature-engineering steps were not found. Models — the reported leading classifiers are Logistic Regression and a RoBERTa-based transformer; TF-IDF also appears in the hyperparameter table. Results — on the validation set, with metrics ordered Accuracy, Precision, Recall, and F1 Score, Logistic Regression reports 0.91, 0.62, 0.72, and 0.65; RoBERTa reports 0.97, 0.88, 0.77, and 0.81. The paper identifies RoBERTa as its best-performing model. Dashboard — AURORA is presented as a misinformation-classification dashboard at https://misinfo-4.onrender.com/. Limitations — no formal study limitations were found; the paper only warns that free Render hosting may delay loading by about two minutes.

Assessment: The retrieved evidence supports the model names, validation metrics, dashboard URL, and hosting caveat. It is insufficient to assess dataset representativeness, preprocessing reproducibility, test-set performance, statistical uncertainty, baseline fairness, dashboard validation, or generalization claims.
Paper claims (evidence references follow array order): Dataset — retrieved excerpts do not establish size, composition, labels, languages, collection method, or splits. Preprocessing — no cleaning, normalization, tokenization, or feature-engineering procedure is documented in the available evidence. Models — Logistic Regression and a RoBERTa-based transformer were evaluated on a validation set [E1]; TF-IDF is also listed, but its exact role is unclear [E4]. Results — the reported metric order is Accuracy, Precision, Recall, and F1 Score [E2]. Logistic Regression reports 0.91, 0.62, 0.72, and 0.65; RoBERTa reports 0.97, 0.88, 0.77, and 0.81 [E3]. Dashboard — the paper describes AURORA as a misinformation-classification dashboard [E5] and provides a Render URL [E6]. Limitations — no formal research limitations were substantiated by the retrieved excerpts.

Assessment: The available evidence supports only the model names, validation metrics, dashboard purpose, and URL. Missing dataset, preprocessing, evaluation-protocol, test-set, uncertainty, and formal limitation details prevent assessment of representativeness, leakage risk, reproducibility, generalization, or dashboard reliability.

> Logistic Regression and RoBERTa based transformer models on the validation set.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Accuracy
Precision
Recall
F1 Score
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Logistic Regression
0.91
0.62
0.72
0.65
RoBERTa based transformer
0.97
0.88
0.77
0.81
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> TF-IDF
Logistic Regression
RoBERTa
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> We developed a dashboard AURORA from this subtask 3 of misinformation classification model
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

> can be accessed via this link: https://misinfo-4.onrender.com/.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

> this website might cause delay of approx. 2 minutes in showing the webpage.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

> Logistic Regression and RoBERTa based transformer models on the validation set.
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Accuracy
Precision
Recall
F1 Score
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> Logistic Regression
0.91
0.62
0.72
0.65
RoBERTa based transformer
0.97
0.88
0.77
0.81
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> TF-IDF
Logistic Regression
RoBERTa
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk e586f60e-156e-50c5-a74d-347f90399adf

> We developed a dashboard AURORA from this subtask 3 of misinformation classification model
Source: 9a3c3278-3057-5439-901d-d2b725c16cd8 · chunk b6d9a055-a5f1-57e5-ac83-892e38f968cc

Limitation: Exact quotes and explicit numeric relations verified; general semantic entailment is not established.

Citation checks establish exact quotation and source identity, not semantic entailment.