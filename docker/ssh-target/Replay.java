import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class Replay {
    public static void main(String[] args) throws IOException {
        String tradeIds = "data/replay/trade-ids.txt";
        String output = "data/replay/replay.out";

        for (int i = 0; i < args.length - 1; i++) {
            if ("--trade-ids".equals(args[i])) {
                tradeIds = args[i + 1];
            }
            if ("--output".equals(args[i])) {
                output = args[i + 1];
            }
        }

        String host = java.net.InetAddress.getLocalHost().getHostName();
        String idText = Files.exists(Path.of(tradeIds)) ? Files.readString(Path.of(tradeIds)).trim() : "";
        String result = "replay.host=" + host + System.lineSeparator()
            + "replay.tradeIds=" + idText + System.lineSeparator()
            + "replay.status=written" + System.lineSeparator();

        Files.writeString(Path.of(output), result);
        System.out.print(result);
    }
}
