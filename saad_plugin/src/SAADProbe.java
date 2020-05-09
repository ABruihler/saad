import java.util.Map;

public class SAADProbe {
    private String name;
    private String type;
    private Map<String, String>config;

    public SAADProbe() {
        super();
    }

    public SAADProbe(String name, String type, Map<String, String> config) {
        this.name = name;
        this.type = type;
        this.config = config;
    }

    public String getType() {
        return type;
    }

    public Map<String, String> getConfig() {
        return config;
    }

    public String getName() { return name; }

    public boolean removeCondition() {
        if(!config.containsKey("condition")) {
            return false;
        }
        config.remove("condition");
        return true;
    }
}
