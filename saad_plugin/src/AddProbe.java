import com.fasterxml.jackson.core.JsonGenerationException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonMappingException;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.project.Project;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.intellij.openapi.ui.DialogWrapper;
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

    public static String readFile(File file) throws IOException {
        return new String(Files.readAllBytes(file.toPath()));
    }

    public static boolean generateProbeJSON(List<SAADProbe> probeList, String path) {
        ObjectMapper mapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);

        for (SAADProbe probe : probeList) {
            if (probe.getConfig().get("condition").equals("None") || probe.getConfig().get("condition").equals("")) {
                probe.removeCondition();
            }
        }
        try {
            mapper.writeValue(new File(path), probeList);
            return true;
        } catch (JsonGenerationException e) {
            e.printStackTrace();
        } catch (JsonMappingException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }

        return false;
    }

    public static List<SAADProbe> readProbeJSON(String path) {
        ObjectMapper mapper = new ObjectMapper();
        File probeFile = new File(path);
        List<SAADProbe> probeList = null;
        try {
            probeList = mapper.readValue(probeFile, new TypeReference<List<SAADProbe>>() {});
        } catch (IOException e) {
            e.printStackTrace();
        }
        return probeList;
    }

    public static Map<String, Map<String, String>> jsonToMap(String jsonString) {
        ObjectMapper mapper = new ObjectMapper();
        Map<String, Map<String, String>> map = new HashMap<>();
        try {
            map = mapper.readValue(jsonString, Map.class);
        } catch (IOException e) {
            e.printStackTrace();
        }

        return map;
    }

    public static List<SAADModule> getModules(Map<String, Map<String, String>> jsonMap) {
        List<SAADModule> moduleList = new ArrayList<SAADModule>();
        for (Map.Entry<String, Map<String, String>> module : jsonMap.entrySet()) {
            String moduleName = module.getKey();
            moduleList.add(new SAADModule(moduleName, jsonMap.get(moduleName).get("command")));
        }
        return moduleList;
    }

    @Override
    public void update(AnActionEvent anActionEvent) {
    }

    @Override
    public void actionPerformed(@NotNull AnActionEvent event) {
        Project currentProject = event.getProject();
        String projectDirectory = currentProject.getBasePath();
        File saadDirectory = new File(projectDirectory + "/SAAD");
        if (!saadDirectory.exists() || !saadDirectory.isDirectory()) {
            System.err.println("SAAD directory not found - must have SAAD directory within project repository.");
            return;
        }
        File probeConfigs = new File(saadDirectory + "/probe_configs");
        File moduleConfigs = new File(saadDirectory + "/module_configs");
        if (!moduleConfigs.exists() || !moduleConfigs.isDirectory() || moduleConfigs.list().length == 0) {
            System.err.println("No module configurations found");
            return;
        }
        if (!probeConfigs.exists() || !probeConfigs.isDirectory()) {
            probeConfigs.mkdir();
        }


        Map<String, Map<String, String>> moduleMap = new HashMap<>();
        for (File file : moduleConfigs.listFiles()) {
            String jsonString;
            try {
                jsonString = readFile(file);
            } catch (IOException e) {
                System.err.println("Error reading module configs.");
                return;
            }

            Map<String, Map<String, String>> map = jsonToMap(jsonString);
            moduleMap.putAll(map);
        }

        List<SAADModule> moduleList = getModules(moduleMap);
        List<String> referenceProbes = new ArrayList<>();
        List<SAADProbe> probes = new ArrayList<>();

        while (true) {

            ModuleSelectDialog moduleSelectDialog = new ModuleSelectDialog(moduleList);
            if (!moduleSelectDialog.showAndGet()) {
                break;
            }

            AddProbeDialog addProbeDialog = new AddProbeDialog(currentProject, moduleSelectDialog.getSelectedModule(), referenceProbes);
            addProbeDialog.show();

            Map<String, String> probeConfig = new HashMap<>();
            for (String key : addProbeDialog.getParameterEntries().keySet()) {
                probeConfig.put(key, (String) addProbeDialog.getParameterEntries().get(key).getSelectedItem());
            }
            if (addProbeDialog.getSpecifyFile()) {
                Path absolutePath = Paths.get(addProbeDialog.getTargetFile());
                try {
                    probeConfig.put("file", Paths.get(projectDirectory).relativize(absolutePath).toString());
                } catch (IllegalArgumentException e) {
                    e.printStackTrace();
                }
            }
            probes.add(new SAADProbe(addProbeDialog.getName(), addProbeDialog.getProbeTypeName(), probeConfig));

            if (addProbeDialog.getExitCode() == AddProbeDialog.FINISH_EXIT_CODE) {
                break;
            }

            referenceProbes.add("{" + addProbeDialog.getName() + "}");
        }

        if (probes.size() > 0) {
            NameProbeFileDialog nameProbeFileDialog = new NameProbeFileDialog();
            nameProbeFileDialog.show();

            if (nameProbeFileDialog.getExitCode() == DialogWrapper.CANCEL_EXIT_CODE) {
                return;
            }

            String probeFileName = nameProbeFileDialog.getName();
            if (probeFileName.length() > 5 && probeFileName.substring(probeFileName.length() - 5).equals(".json")) {
                probeFileName = probeFileName.substring(0, probeFileName.length() - 5);
            }

            if (generateProbeJSON(probes, saadDirectory + "/probe_configs/" + probeFileName + ".json")) {
                ProbeConfirmationDialog probeConfirmationDialog = new ProbeConfirmationDialog();
                probeConfirmationDialog.show();
            }
        }
    }
}
