import java.util.Map;

/*
Object representation of probe.
 */
public class SAADProbe {
    private String name;
    private String type;
    private Map<String, String>config;

    public SAADProbe() {
        super();
    }

    /*
    * Constructor for probe objects.
    *
    * @param name   The name of the probe
    * @param type   The module associated with the probe
    * @param config The parameters of the probe (maps name of the parameter to its value)
     */
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
