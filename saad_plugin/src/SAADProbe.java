import java.util.HashMap;
import java.util.Map;

public class SAADProbe {
    private String type;
    private Map<String, String>config;

    public SAADProbe(String type, Map<String, String> config) {
        this.type = type;
        this.config = config;
    }

    public String getType() {
        return type;
    }

    public Map<String, String> getConfig() {
        return config;
    }

}
