# AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10

# Install system graphic libraries required by Pillow / OpenCV
RUN yum update -y && \
    yum install -y mesa-libGL gcc-c++ && \
    yum clean all

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# Install CPU-only PyTorch first (drastically reduces image size from 2.5GB to ~800MB)
RUN pip install --no-cache-dir \
    torch==2.3.1 torchvision==0.18.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install
COPY lambda/requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Pre-download FaceNet pretrained weights into image layer to eliminate runtime cold-start downloads
RUN python3 -c "from facenet_pytorch import InceptionResnetV1, MTCNN; MTCNN(); InceptionResnetV1(pretrained='vggface2')"

# Copy application packages
COPY backend/ ${LAMBDA_TASK_ROOT}/backend/
COPY ml/ ${LAMBDA_TASK_ROOT}/ml/
COPY lambda/handler.py ${LAMBDA_TASK_ROOT}/handler.py

# Set entry point
CMD [ "handler.lambda_handler" ]
