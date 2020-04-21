import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SAADModule {

    private String moduleName;
    private List<String> parameters;

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
        while(m.find()) {
            parameters.add(m.group(1));
        }
    }

    public List<String> getParameters() {
        return parameters;
    }
}
