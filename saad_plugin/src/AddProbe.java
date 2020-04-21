import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.actionSystem.CommonDataKeys;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.Messages;
import com.intellij.pom.Navigatable;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.jetbrains.annotations.NotNull;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class AddProbe extends AnAction {

    public String readFile(File file) throws IOException {
        return new String(Files.readAllBytes(file.toPath()));
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

        // for choosing files to probe, not implemented yet just placeholder code
        //TextFieldWithBrowseButton fileChooser = new TextFieldWithBrowseButton();
        //fileChooser.addBrowseFolderListener("Title", "Description", currentProject, new FileChooserDescriptor(true, false, false, false, false, false));

        // irrelevant (copied) code for testing
        StringBuffer dlgMsg = new StringBuffer(event.getPresentation().getText() + " Selected!");
        String dlgTitle = event.getPresentation().getDescription();
        // If an element is selected in the editor, add info about it.
        Navigatable nav = event.getData(CommonDataKeys.NAVIGATABLE);
        if (nav != null) {
            dlgMsg.append(String.format("\nSelected Element: %s", moduleList.get(5).getParameters()));
        }
        Messages.showMessageDialog(currentProject, dlgMsg.toString(), dlgTitle, Messages.getInformationIcon());

    }
}
