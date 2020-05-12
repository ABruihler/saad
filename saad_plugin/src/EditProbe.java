import com.intellij.openapi.actionSystem.AnAction;
import com.intellij.openapi.actionSystem.AnActionEvent;
import com.intellij.openapi.project.Project;
import org.jetbrains.annotations.NotNull;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class EditProbe extends AnAction {

    @Override
    public void actionPerformed(@NotNull AnActionEvent event) {
        Project currentProject = event.getProject();
        String projectDirectory = currentProject.getBasePath();
        File saadDirectory = new File(projectDirectory + "/SAAD");
        if(!saadDirectory.exists() || !saadDirectory.isDirectory()) {
            System.err.println("SAAD directory not found - must have SAAD directory within project repository.");
            return;
        }

        File probeConfigs = new File(saadDirectory + "/probe_configs");
        if(!probeConfigs.exists() || !probeConfigs.isDirectory()){
            System.err.println("Probe configurations directory not found - must have probe_configs directory within project repository.");
        }

        // Iterate through probe files in probe_configs directory
        Map<String, List<SAADProbe>> probeFileMap = new HashMap<>();
        for(File file : probeConfigs.listFiles()) {
            // Create lists of SAADProbe objects (one for each file) (Map name to list of probes)
            probeFileMap.put(file.getName(), AddProbe.readProbeJSON(file.getPath()));
        }
        // File Select Dialog - select file name
        FileSelectDialog fileSelectDialog = new FileSelectDialog(probeFileMap);
        fileSelectDialog.show();
        String fileName = fileSelectDialog.getSelectedFile();
        List<SAADProbe> probesToEdit = AddProbe.readProbeJSON(probeConfigs + "/" + fileName);

        // Edit Probe Dialog - Allow editing all fields for probes in file
        EditProbeDialog editProbeDialog = new EditProbeDialog(currentProject, probesToEdit);
        editProbeDialog.show();
        // Write Probe File (Overwrite)
    }
}
