import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;
import com.intellij.ui.components.JBTextField;

import javax.annotation.Nullable;
import javax.swing.*;
import java.awt.*;

public class AddProbeDialog extends DialogWrapper {

    private Project currentProject;
    private SAADModule probeType;
    private boolean specifyFile;

    public AddProbeDialog(Project currentProject, SAADModule probeType) {
        super(true); // use current window as parent

        this.currentProject = currentProject;
        this.probeType = probeType;
        this.specifyFile = false;

        init();
        setTitle("Configure Probes");
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
                JBTextField textField = new JBTextField();
                label.setLabelFor(textField);
                dialogPanel.add(textField);
            }
        }
        if(this.specifyFile) {
            JLabel label = new JLabel("File");
            dialogPanel.add(label);
            TextFieldWithBrowseButton textField = new TextFieldWithBrowseButton();
            textField.addBrowseFolderListener("Title", "Description", currentProject, new FileChooserDescriptor(true, false, false, false, false, false));
            label.setLabelFor(textField);
            dialogPanel.add(textField);
        }

        return dialogPanel;
    }
}
