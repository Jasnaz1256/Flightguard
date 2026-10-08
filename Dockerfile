FROM public.ecr.aws/lambda/python:3.10

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api/ ${LAMBDA_TASK_ROOT}/api/
COPY model/risk.py ${LAMBDA_TASK_ROOT}/model/
COPY model/flightguard_delay.pkl ${LAMBDA_TASK_ROOT}/model/
COPY model/*.parquet ${LAMBDA_TASK_ROOT}/model/

CMD ["api.main.handler"]