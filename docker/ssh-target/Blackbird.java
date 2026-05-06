import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class Blackbird {
    public static void main(String[] args) throws IOException {
        String config = "config/environment.conf";
        String log = "log/trading/blackbird.log";

        for (int i = 0; i < args.length - 1; i++) {
            if ("--config".equals(args[i])) {
                config = args[i + 1];
            }
            if ("--log".equals(args[i])) {
                log = args[i + 1];
            }
        }

        String host = java.net.InetAddress.getLocalHost().getHostName();
        String configText = Files.exists(Path.of(config)) ? Files.readString(Path.of(config)) : "";
        boolean debug = configText.contains("loggingLevel=DEBUG") || configText.contains("log.level=DEBUG");
        String level = debug ? "DEBUG" : "INFO";
        StringBuilder result = new StringBuilder();
        result.append("blackbird.host=").append(host).append(System.lineSeparator());
        result.append("blackbird.level=").append(level).append(System.lineSeparator());
        result.append("INFO startup replay initialized").append(System.lineSeparator());
        if (debug) {
            result.append("DEBUG loaded inbound transaction log").append(System.lineSeparator());
            result.append("DEBUG expanded recovery state").append(System.lineSeparator());
        }

        Files.createDirectories(Path.of(log).getParent());
        Files.writeString(Path.of(log), result.toString());
        System.out.print(result);
    }
}
