import com.intellij.openapi.ui.DialogWrapper;

import javax.annotation.Nullable;
import javax.swing.*;
import java.awt.*;

/*
Simple dialog to alert user that a probe configuration file was generated successfully.
 */

public class ProbeConfirmationDialog extends DialogWrapper {

    public ProbeConfirmationDialog() {
        super(true);
        init();
        setTitle("Configure Probes");
    }

    @Nullable
    @Override
    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel();
        dialogPanel.setLayout(new BorderLayout());
        JLabel label = new JLabel("Probe added successfully.");
        dialogPanel.add(label);
        return dialogPanel;

    }

    @Override
    protected Action[] createActions() {
        return new Action[]{getOKAction()};
    }
}
