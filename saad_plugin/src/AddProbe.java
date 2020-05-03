import com.fasterxml.jackson.core.JsonGenerationException;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;
import com.intellij.pom.Navigatable;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.intellij.ui.components.JBTextField;
import org.jetbrains.annotations.NotNull;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class AddProbe extends AnAction {

    public String readFile(File file) throws IOException {
        return new String(Files.readAllBytes(file.toPath()));
    }

    public void generateProbeJSON(String type, Map<String, String> config, String path) {
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);

        SAADProbe probe = new SAADProbe(type, config);
        try {
            mapper.writeValue(new File(path), probe);
        } catch (JsonGenerationException e) {
            e.printStackTrace();
        } catch (JsonMappingException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public Map<String, Map<String, String>> jsonToMap(String jsonString) {
        ObjectMapper mapper = new ObjectMapper();
        Map<String, Map<String, String>> map = new HashMap<>();
        try {
            map = mapper.readValue(jsonString, Map.class);
        } catch (IOException e) {
            e.printStackTrace();
        }

        return map;
    }

    public List<SAADModule> getModules(Map<String, Map<String, String>> jsonMap) {
        List<SAADModule> moduleList = new ArrayList<SAADModule>();
        for(Map.Entry<String, Map<String, String>> module : jsonMap.entrySet()) {
            String moduleName = module.getKey();
            moduleList.add(new SAADModule(moduleName, jsonMap.get(moduleName).get("command")));
        }
        return moduleList;
    }


    @Override
    public void update(AnActionEvent anActionEvent){

    }
    @Override
    public void actionPerformed(@NotNull AnActionEvent event) {
        Project currentProject = event.getProject();
        String projectDirectory = currentProject.getBasePath();
        File saadDirectory = new File(projectDirectory + "/SAAD");
        if(!saadDirectory.exists() || !saadDirectory.isDirectory()) {
            System.err.println("SAAD directory not found");
            return;
        }
        File probeConfigs = new File(saadDirectory + "/probe_configs");
        File moduleConfigs = new File(saadDirectory + "/module_configs");
        if(!moduleConfigs.exists() || !moduleConfigs.isDirectory() || moduleConfigs.list().length == 0){
            System.err.println("No module configurations found");
            return;
        }
        if(!probeConfigs.exists() || !probeConfigs.isDirectory()){
            probeConfigs.mkdir();
        }


        Map<String, Map<String, String>> moduleMap = new HashMap<>();
        for (File file : moduleConfigs.listFiles()) {
            String jsonString;
            try{
               jsonString = readFile(file);
            } catch (IOException e) {
                System.err.println("Error reading module configs.");
                return;
            }

            Map<String, Map<String, String>> map = jsonToMap(jsonString);
            moduleMap.putAll(map);
        }

        List<SAADModule> moduleList = getModules(moduleMap);

        ModuleSelectDialog moduleSelectDialog = new ModuleSelectDialog(moduleList);
        moduleSelectDialog.show();

        AddProbeDialog addProbeDialog = new AddProbeDialog(currentProject, moduleSelectDialog.getSelectedModule());
        addProbeDialog.show();

        Map<String, String> probeConfig = new HashMap<>();
        for(String key: addProbeDialog.getParameterEntries().keySet()) {
            probeConfig.put(key, addProbeDialog.getParameterEntries().get(key).getText());
        }
        if(addProbeDialog.getSpecifyFile()) {
            Path absolutePath = Paths.get(addProbeDialog.getTargetFile().getText());
            probeConfig.put("file", Paths.get(projectDirectory).relativize(absolutePath).toString());
        }

        generateProbeJSON(addProbeDialog.getProbeTypeName(), probeConfig, saadDirectory + "/probe_configs/test.json");
    }
}
