import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;
import com.intellij.ui.EditorTextField;
import com.intellij.ui.components.JBTextField;

import javax.annotation.Nullable;
import javax.swing.*;
import java.awt.*;
import java.util.HashMap;
import java.util.Map;

public class AddProbeDialog extends DialogWrapper {

    private Project currentProject;
    private SAADModule probeType;
    private boolean specifyFile;
    private Map<String, EditorTextField>  parameterEntries;
    private TextFieldWithBrowseButton targetFile;

    public AddProbeDialog(Project currentProject, SAADModule probeType) {
        super(true); // use current window as parent

        this.currentProject = currentProject;
        this.probeType = probeType;
        this.specifyFile = false;
        this.parameterEntries = new HashMap<>();

        init();
        setTitle("Add Probes");
    }

    @Nullable
    @Override
    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel();
        dialogPanel.setLayout(new GridLayout(0, 2));

        for (String parameter : probeType.getParameters()) {
            if(parameter.toLowerCase().equals("file")) {
                this.specifyFile = true;
            } else if(!parameter.toLowerCase().equals("head") && !parameter.toLowerCase().equals("head~1")) {
                JLabel label = new JLabel(parameter.substring(0,1).toUpperCase() + parameter.substring(1));
                dialogPanel.add(label);
                EditorTextField textField = new EditorTextField();
                label.setLabelFor(textField);
                this.parameterEntries.put(parameter, textField);
                dialogPanel.add(textField);
            }
        }
        if(this.specifyFile) {
            JLabel label = new JLabel("File");
            dialogPanel.add(label);
            this.targetFile = new TextFieldWithBrowseButton();
            FileChooserDescriptor descriptor = new FileChooserDescriptor(true, false, false, false, false, false);
            descriptor.setRoots(ProjectRootManager.getInstance(currentProject).getContentRoots());
            this.targetFile.addBrowseFolderListener("Title", "Description", currentProject, descriptor);
            label.setLabelFor(this.targetFile);
            dialogPanel.add(this.targetFile);
        }
        return dialogPanel;
    }

    public String getProbeTypeName() {
        return this.probeType.getModuleName();
    }

    public Map<String, EditorTextField> getParameterEntries() {
        return this.parameterEntries;
    }

    public TextFieldWithBrowseButton getTargetFile() {
        return targetFile;
    }

    public boolean getSpecifyFile() {
        return this.specifyFile;
    }
}
