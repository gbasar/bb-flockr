ARG UBI_IMAGE=registry.access.redhat.com/ubi9/ubi:latest

FROM ${UBI_IMAGE}

USER root

WORKDIR /workspace/flockr

COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples
COPY tests/e2e ./tests/e2e

RUN dnf install -y python3.12 python3.12-pip openssh-clients && \
    dnf clean all

RUN python3.12 -m pip install --upgrade pip && \
    python3.12 -m pip install ".[hocon]"

RUN ln -s /usr/local/bin/flockr /usr/bin/flockr

CMD ["flockr", "--help"]
