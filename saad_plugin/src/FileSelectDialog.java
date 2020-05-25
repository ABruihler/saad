import com.intellij.openapi.ui.ComboBox;
import com.intellij.openapi.ui.DialogWrapper;

import javax.annotation.Nullable;
import javax.swing.*;
import java.awt.*;
import java.util.List;
import java.util.Map;

/**
 * Dialog for selecting a file from probe configs.
 */
public class FileSelectDialog extends DialogWrapper {

    private Map<String, List<SAADProbe>> probeFileMap;
    private ComboBox fileSelectField;

    /**
     * Constructor for file select dialog.
     *
     * @param probeFileMap   A map of probe file names to their contents as a list of probe objects.
     */
    public FileSelectDialog(Map<String, List<SAADProbe>> probeFileMap) {
        super(true);

        this.probeFileMap = probeFileMap;

        init();
        setTitle("Select File");
    }

    @Nullable
    @Override
    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel();
        dialogPanel.setLayout(new BorderLayout());

        this.fileSelectField = new ComboBox(probeFileMap.keySet().toArray());
        dialogPanel.add(this.fileSelectField, BorderLayout.CENTER);
        return dialogPanel;
    }

    public String getSelectedFile() {
        return this.fileSelectField.getSelectedItem().toString();
    }
}
