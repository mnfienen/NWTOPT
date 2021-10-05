FROM python:3.8-slim-buster

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get -y upgrade  && \
    apt-get install -y --no-install-recommends \
    git \
    wget \
    curl \
    unzip \
    g++ \
    gcc \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY conda_requirements.yml /opt/conda_requirements.yml

ENV PATH="/root/miniconda3/bin:${PATH}"
ARG PATH="/root/miniconda3/bin:${PATH}"
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-latest-Linux-x86_64.sh -b \
    && rm -f Miniconda3-latest-Linux-x86_64.sh \
    echo "Running $(conda --version)" && \
    conda init bash && \
    . /root/.bashrc && \
    conda update conda  && \
    conda env create -f /opt/conda_requirements.yml && \
    conda clean --all -f -y && \
    conda activate nwtenv

# get the MODFLOW binaries
RUN curl -L -o linux.zip https://github.com/MODFLOW-USGS/executables/releases/latest/download/linux.zip?raw=true \
&& mkdir /opt/binaries \
&& unzip linux.zip -d /opt/binaries \
&& rm linux.zip 

# add binaries to the path
ENV PATH="/opt/binaries:${PATH}"

WORKDIR /app
COPY . /app

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
# For more info, please refer to https://aka.ms/vscode-docker-python-configure-containers
#RUN adduser -u 5678 --disabled-password --gecos "" appuser && chown -R appuser /app && \
#        chown -R appuser /root/miniconda3
#USER appuser

#RUN conda init bash 

#RUN . /home/appuser/.bashrc
# Make RUN commands use the new environment:
SHELL ["conda", "run", "-n", "nwtenv", "/bin/bash", "-c"]

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
ENTRYPOINT ["conda", "run", "--no-capture-output", "-n", "nwtenv", "python", "NWT_SUBMIT/NWTOPT_FILES/optimize_NWT.py"]
