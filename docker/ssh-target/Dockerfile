ARG UBI_OPENJDK_IMAGE=registry.access.redhat.com/ubi9/openjdk-17:latest
ARG UBI_MINIMAL_IMAGE=registry.access.redhat.com/ubi9/ubi-minimal:latest

FROM ${UBI_OPENJDK_IMAGE} AS app-builder

WORKDIR /tmp/flockr-apps

COPY Replay.java Blackbird.java ./

RUN javac Replay.java Blackbird.java && \
    jar --create --file replay.jar --main-class Replay Replay.class && \
    jar --create --file blackbird.jar --main-class Blackbird Blackbird.class


FROM ${UBI_MINIMAL_IMAGE}

RUN microdnf install -y java-17-openjdk-headless openssh-server shadow-utils hostname && \
    microdnf clean all && \
    useradd -m -d /home/flockr flockr && \
    mkdir -p \
        /home/flockr/.ssh \
        /apps/flockr/data/archive \
        /apps/flockr/data/replay \
        /appBaseDir/shard1/trading/app/trading/bin \
        /appBaseDir/shard1/trading/app/trading/lib \
        /appBaseDir/shard1/trading/app/trading/lib/native \
        /appBaseDir/shard1/trading/app/trading/lib/solaceSSL \
        /appBaseDir/shard1/trading/config \
        /appBaseDir/shard1/trading/data/trading/archive \
        /appBaseDir/shard1/trading/data/trading/txn-log \
        /appBaseDir/shard1/trading/log/trading && \
    printf "TRADE-1\nTRADE-2\n" > /apps/flockr/data/replay/trade-ids.txt && \
    printf "loggingLevel=ERROR\nlog.level=ERROR\nenvironment=PRD\n" > /appBaseDir/shard1/trading/config/environment.conf && \
    printf "outbound trade txn log\n" > /appBaseDir/shard1/trading/log/trading/trading.data-timestamp.log && \
    printf "inbound trade txn log\n" > /appBaseDir/shard1/trading/data/trading/txn-log/trading-solace-inbound-messages-2026-4-31.shard-1.rdat.in && \
    printf "archive payload\n" > /appBaseDir/shard1/trading/data/trading/archive/trading-shard11-20260430.00.00.00.123.tar.gz && \
    printf "#!/usr/bin/env sh\njava -jar app/trading/lib/blackbird.jar --config config/environment.conf --log log/trading/blackbird.log\n" > /appBaseDir/shard1/trading/app/trading/bin/start.sh && \
    chmod +x /appBaseDir/shard1/trading/app/trading/bin/start.sh && \
    chown -R flockr:flockr /home/flockr /apps/flockr && \
    chown -R flockr:flockr /appBaseDir && \
    ssh-keygen -A

COPY authorized_keys /home/flockr/.ssh/authorized_keys
COPY --from=app-builder /tmp/flockr-apps/replay.jar /apps/flockr/replay.jar
COPY --from=app-builder /tmp/flockr-apps/blackbird.jar /appBaseDir/shard1/trading/app/trading/lib/blackbird.jar

RUN chown -R flockr:flockr /apps/flockr /appBaseDir /home/flockr/.ssh && \
    chmod 700 /home/flockr/.ssh && \
    chmod 600 /home/flockr/.ssh/authorized_keys

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e"]
