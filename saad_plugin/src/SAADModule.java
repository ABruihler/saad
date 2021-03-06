import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Class for storing object representation of modules.
 */
public class SAADModule {

    private String moduleName;
    private List<String> parameters;

    /**
     * Constructor for module object.
     *
     * @param moduleName     The name of the module
     * @param command        The command line command associated with the module (with parameters indicated by {})
     */
    public SAADModule(String moduleName, String command) {
        this.moduleName = moduleName;
        this.parameters = new ArrayList<>();
        this.setParametersFromCommand(command);
    }

    public SAADModule(String moduleName, List<String> parameters) {
        this.moduleName = moduleName;
        this.parameters = parameters;
    }

    public void setParametersFromCommand(String command) {
        Matcher m = Pattern.compile("\\{([^}]+)\\}").matcher(command);
        while (m.find()) {
            parameters.add(m.group(1));
        }
    }

    public String getModuleName() {
        return this.moduleName;
    }

    public List<String> getParameters() {
        return this.parameters;
    }
}
