import com.intellij.openapi.ui.ComboBox;
import com.intellij.openapi.ui.DialogWrapper;

import javax.swing.*;
import java.awt.*;
import java.util.ArrayList;
import java.util.List;

public class ModuleSelectDialog extends DialogWrapper {

    List<SAADModule> moduleList;
    private ComboBox<String> moduleSelectField;

    public ModuleSelectDialog(List<SAADModule> moduleList) {
        super(true);
        this.moduleList = moduleList;
        init();
        setTitle("Select Module");
    }

    protected JComponent createCenterPanel() {
        JPanel dialogPanel = new JPanel(new BorderLayout());

        JLabel label = new JLabel("Select module:");
        label.setPreferredSize(new Dimension(100, 100));

        List<String> moduleOptions = new ArrayList<>();
        for (SAADModule module : this.moduleList) {
            moduleOptions.add(module.getModuleName());
        }

        this.moduleSelectField = new ComboBox(moduleOptions.toArray());
        label.setLabelFor(this.moduleSelectField);
        dialogPanel.add(this.moduleSelectField, BorderLayout.CENTER);

        return dialogPanel;
    }

    public SAADModule getSelectedModule() {
        return moduleList.get(this.moduleSelectField.getSelectedIndex());
    }
}
