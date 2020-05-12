import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.ui.ComboBox;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;
import com.intellij.ui.EditorTextField;

import javax.swing.*;
import java.awt.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class EditProbeDialog extends DialogWrapper {

    private class ProbeInterface {
        private EditorTextField nameField;
        private Map<String, EditorTextField> parameterEntries;
        private TextFieldWithBrowseButton targetFile;
        private boolean specifyFile;
        private String probeType;

        public ProbeInterface(String probeType) {
            this.nameField = new EditorTextField();
            this.parameterEntries = new HashMap<>();
            this.specifyFile = false;
            this.probeType = probeType;
        }
    }

    private List<SAADProbe> probes;
    private List<ProbeInterface> probeFields;
    private Project currentProject;

    public EditProbeDialog(Project currentProject, List<SAADProbe> probesToEdit) {
        super(true);

        this.currentProject = currentProject;
        this.probes = probesToEdit;
        this.probeFields = new ArrayList<>();

        init();
        setTitle("Edit Probe Fields");
    }

    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel();

        dialogPanel.setLayout(new GridLayout(0, 2));

        for(SAADProbe probe : this.probes) {
            ProbeInterface probeInterface = new ProbeInterface(probe.getType());
            this.probeFields.add(probeInterface);
            JLabel nameLabel = new JLabel("Probe Name");
            dialogPanel.add(nameLabel);
            nameLabel.setLabelFor(probeInterface.nameField);
            probeInterface.nameField.setText(probe.getName());
            dialogPanel.add(probeInterface.nameField);

            for (String parameter : probe.getConfig().keySet()) {
                if (parameter.toLowerCase().equals("file")) {
                    probeInterface.specifyFile = true;
                } else if (!parameter.toLowerCase().equals("head") && !parameter.toLowerCase().equals("head~1")) {
                    JLabel label = new JLabel(parameter.substring(0, 1).toUpperCase() + parameter.substring(1));
                    dialogPanel.add(label);
                    EditorTextField textField = new EditorTextField();
                    textField.setText(probe.getConfig().get(parameter));
                    label.setLabelFor(textField);
                    probeInterface.parameterEntries.put(parameter, textField);
                    dialogPanel.add(textField);
                }
            }
            if (probeInterface.specifyFile) {
                JLabel label = new JLabel("File");
                dialogPanel.add(label);
                probeInterface.targetFile = new TextFieldWithBrowseButton();
                FileChooserDescriptor descriptor = new FileChooserDescriptor(true, false, false, false, false, false);
                descriptor.setRoots(ProjectRootManager.getInstance(currentProject).getContentRoots());
                probeInterface.targetFile.addBrowseFolderListener("Select File", "", currentProject, descriptor);
                probeInterface.targetFile.setText(probe.getConfig().get("file"));
                label.setLabelFor(probeInterface.targetFile);
                dialogPanel.add(probeInterface.targetFile);
            }
            // add condition
            JLabel conditionLabel = new JLabel("Condition");
            dialogPanel.add(conditionLabel);
            EditorTextField conditionField = new EditorTextField();
            conditionField.setText(probe.getConfig().get("condition"));
            probeInterface.parameterEntries.put("condition", conditionField);
            dialogPanel.add(conditionField);
        }

        return dialogPanel;
    }

    public List<SAADProbe> getProbes() {
        this.probes = new ArrayList<>();
        for (ProbeInterface probeInterface : probeFields) {
            String name = probeInterface.nameField.getText();
            String type = probeInterface.probeType;
            Map<String, String> config = new HashMap<>();
            for(String parameter : probeInterface.parameterEntries.keySet()) {
                config.put(parameter, probeInterface.parameterEntries.get(parameter).getText());
            }
            this.probes.add(new SAADProbe(name, type, config));
        }
        return this.probes;
    }
}
