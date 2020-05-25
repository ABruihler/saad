import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.roots.ProjectRootManager;
import com.intellij.openapi.ui.ComboBox;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;
import com.intellij.ui.EditorTextField;

import javax.annotation.Nullable;
import javax.swing.*;
import java.awt.*;
import java.util.HashMap;
import java.util.Map;
import java.util.List;
import java.util.ArrayList;

/*
Dialog for adding a probe of a given type.
 */

public class AddProbeDialog extends DialogWrapper {

    // Rename exit codes to correspond with dialog buttons
    public static final int ADD_ANOTHER_PROBE_EXIT_CODE = DialogWrapper.CANCEL_EXIT_CODE;
    public static final int FINISH_EXIT_CODE = DialogWrapper.OK_EXIT_CODE;

    private Project currentProject;
    private SAADModule probeType;
    private boolean specifyFile;
    private Map<String, ComboBox>  parameterEntries;
    private TextFieldWithBrowseButton targetFile;
    private List<String> referenceProbes;
    private EditorTextField nameField;

    /*
    * Constructor for add probe dialog.
    *
    * @param currentProject     The IDEA project for which LOSCAT is implemented
    * @param probeType          The module associated with the probe being added.
    * @param referenceProbes    A list of probes already defined in the current probe file which might be referenced by the current probe.
     */
    public AddProbeDialog(Project currentProject, SAADModule probeType, List<String> referenceProbes) {
        super(true); // use current window as parent

        this.currentProject = currentProject;
        this.probeType = probeType;
        this.specifyFile = false;
        this.parameterEntries = new HashMap<>();
        this.referenceProbes = referenceProbes;
        this.nameField = new EditorTextField();

        this.setOKButtonText("Finish");
        this.setCancelButtonText("Add Another Probe");

        init();
        setTitle("Add Probes");
    }

    @Nullable
    @Override
    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel();
        dialogPanel.setLayout(new GridLayout(0, 2));

        JLabel nameLabel = new JLabel("Probe Name");
        dialogPanel.add(nameLabel);
        nameLabel.setLabelFor(this.nameField);
        dialogPanel.add(nameField);

        // Iterate through parameters associated with current module
        // and add corresponding text fields
        for (String parameter : probeType.getParameters()) {
            if(parameter.toLowerCase().equals("file")) {
                this.specifyFile = true;
            } else if(!parameter.toLowerCase().equals("head") && !parameter.toLowerCase().equals("head~1")) {
                JLabel label = new JLabel(parameter.substring(0,1).toUpperCase() + parameter.substring(1));
                dialogPanel.add(label);
                ComboBox textField = new ComboBox(referenceProbes.toArray());
                textField.setEditable(true);
                textField.addItem("");
                textField.setSelectedItem("");
                label.setLabelFor(textField);
                this.parameterEntries.put(parameter, textField);
                dialogPanel.add(textField);
            }
        }

        // Add text field with browser button if one of the parameters requires a file to be added
        if(this.specifyFile) {
            JLabel label = new JLabel("File");
            dialogPanel.add(label);
            this.targetFile = new TextFieldWithBrowseButton();
            FileChooserDescriptor descriptor = new FileChooserDescriptor(true, false, false, false, false, false);
            descriptor.setRoots(ProjectRootManager.getInstance(currentProject).getContentRoots());
            this.targetFile.addBrowseFolderListener("Select File", "", currentProject, descriptor);
            label.setLabelFor(this.targetFile);
            dialogPanel.add(this.targetFile);
        }
        // add condition
        JLabel conditionLabel = new JLabel("Condition");
        dialogPanel.add(conditionLabel);
        ComboBox conditionField = new ComboBox(referenceProbes.toArray());
        conditionField.setEditable(true);
        conditionField.addItem("None");
        conditionField.setSelectedItem("None");
        this.parameterEntries.put("condition", conditionField);
        dialogPanel.add(conditionField);

        return dialogPanel;
    }

    public String getProbeTypeName() {
        return this.probeType.getModuleName();
    }

    public Map<String, ComboBox> getParameterEntries() {
        return this.parameterEntries;
    }

    public String getTargetFile() {
        return targetFile.getText();
    }

    public boolean getSpecifyFile() {
        return this.specifyFile;
    }

    public String getName() {
        return this.nameField.getText();
    }
}
