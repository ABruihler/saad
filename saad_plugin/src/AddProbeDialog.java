import com.intellij.openapi.fileChooser.FileChooserDescriptor;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.openapi.ui.TextFieldWithBrowseButton;

import javax.annotation.Nullable;
import javax.swing.*;
import java.awt.*;

public class AddProbeDialog extends DialogWrapper {

    private Project currentProject;
    private SAADModule probeType;

    public AddProbeDialog(Project currentProject, SAADModule probeType) {
        super(true); // use current window as parent

        this.currentProject = currentProject;
        this.probeType = probeType;

        init();
        setTitle("Configure Probes");
    }

    @Nullable
    @Override
    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel();
        dialogPanel.setLayout(new BoxLayout(dialogPanel, BoxLayout.Y_AXIS));

        JLabel label = new JLabel("Test");
        label.setPreferredSize(new Dimension(100, 100));

        for (String parameter : probeType.getParameters()) {
            TextFieldWithBrowseButton textField = new TextFieldWithBrowseButton();
            if(parameter.toLowerCase() == "file") {
                textField.addBrowseFolderListener("Title", "Description", currentProject, new FileChooserDescriptor(true, false, false, false, false, false));
            }
            dialogPanel.add(textField);
        }
        return dialogPanel;
    }
}
