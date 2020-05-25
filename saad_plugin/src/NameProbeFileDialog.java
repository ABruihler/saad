import com.intellij.openapi.ui.DialogWrapper;
import com.intellij.ui.EditorTextField;

import javax.annotation.Nullable;
import javax.swing.*;
import java.awt.*;

/**
 * Simple Dialog for user to enter name for probe file.
 */
public class NameProbeFileDialog extends DialogWrapper {

    private EditorTextField textField;

    public NameProbeFileDialog() {
        super(true);
        this.textField = new EditorTextField();
        init();
        setTitle("Name Probe File");
    }

    @Nullable
    @Override
    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel();
        dialogPanel.setLayout(new BorderLayout());
        JLabel label = new JLabel("Enter Probe File Name:");
        dialogPanel.add(label);
        label.setLabelFor(this.textField);
        dialogPanel.add(this.textField);
        return dialogPanel;
    }

    public String getName() {
        return this.textField.getText();
    }
}
