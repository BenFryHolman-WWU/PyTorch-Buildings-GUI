from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QMenu
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtCore import Qt
from neuromancer.hvac.building_components import RTU, VAVBox, Envelope, SolarGains
from neuromancer.hvac.building import BuildingNode
from property_dialog import PropertyDialog

class ComponentItem(QGraphicsRectItem):
    """Rectangle + text representing a building component"""

    def __init__(self, name, pos, building_model):
        super().__init__(0, 0, 120, 50)

        self.building_model = building_model

        self.setPos(pos)
        self.setBrush(QColor(100, 200, 250, 180))
        self.setPen(QPen(QColor(50, 150, 200), 2))

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        self.label.setPos(60 - self.label.boundingRect().width() / 2, 25 - self.label.boundingRect().height() / 2)
        self.component, self.node = self.createComponent(name, building_model.n_zones)
        self.building_model.add_componentItem(self)

    def createComponent(self, name, n_zones):
        match name:
            case "RTU":
                # Create corresponding component
                component = RTU(
                    n_zones=n_zones,
                    airflow_max=4.0,      # Total system capacity [kg/s]
                    airflow_oa_min=0.4,      # Minimum outdoor air [kg/s]
                    Q_coil_max=20000.,     # Heating/cooling capacity [W]
                    fan_power_per_flow=800.,  # Fan efficiency [W/(kg/s)]
                    cooling_COP=3.2,      # Cooling efficiency
                    heating_efficiency=0.88  # Heating efficiency
                )

                # Wrap component as node
                rtu_inputs = {
                    "T_outdoor": "T_outdoor",
                    "envelope.T_zones": "T_return_zones",
                    "vav.supply_airflow": "return_airflow_zones",
                    "rtu_T_supply_setpoint": "T_supply_setpoint",
                    "rtu_supply_airflow_setpoint": "supply_airflow_setpoint",
                    "rtu.damper_position": "damper_position",
                    "rtu.valve_position": "valve_position",
                    "rtu.T_supply": "T_supply",
                    "rtu.integral_accumulator": "integral_accumulator",
                }
                node = BuildingNode(component, input_map=rtu_inputs, name="rtu")

            case "Envelope":
                # Create corresponding component
                component = Envelope(
                    n_zones=n_zones,
                    R_env=self.pad_attribute([0.1, 0.12], n_zones),    # Zone-specific thermal resistance [K/W]
                    C_env=self.pad_attribute([1.2e6, 1.0e6], n_zones),  # Zone-specific thermal mass [J/K]
                    R_internal=0.05,      # Inter-zone resistance [K/W]
                    adjacency=self.pad_matrix([[1.0, 0.0], [0.0, 1.0]], n_zones)  # Identity matrix, seperate zones
                )

                # Wrap component as node
                envelope_inputs = {
                    "envelope.T_zones": "T_zones",
                    "T_outdoor": "T_outdoor",
                    "solar.Q_solar": "Q_solar",
                    "Q_internal": "Q_internal",
                    "vav.Q_supply_flow": "Q_hvac"
                }

                node = BuildingNode(component, input_map=envelope_inputs, name="envelope")

            case "VAVBox":
                # Create corresponding component
                component = VAVBox(
                    n_zones=n_zones,
                    airflow_min=self.pad_attribute([0.1, 0.08], n_zones),     # Zone minimums [kg/s]
                    airflow_max=self.pad_attribute([0.8, 0.6], n_zones),      # Zone maximums [kg/s]
                    control_gain=self.pad_attribute([2.5, 2.0], n_zones),     # Zone control sensitivity
                    Q_reheat_max=self.pad_attribute([3000, 2500], n_zones),  # Zone reheat capacity [W]
                    reheat_efficiency=0.95       # Electric reheat efficiency
                )

                # Wrap component as node
                vav_inputs = {
                    "envelope.T_zones": "T_zone",
                    "vav_T_setpoint": "T_setpoint",
                    "rtu.T_supply": "T_supply_upstream",
                    "rtu.P_supply": "P_duct",
                    "vav.damper_position": "damper_position",
                    "vav.reheat_position": "reheat_position",
                }
                node = BuildingNode(component, input_map=vav_inputs, name="vav")

            case "SolarGains":
                # Create corresponding component
                component = SolarGains(
                    n_zones=n_zones,
                    window_area=25.0,
                    window_orientation=self.pad_attribute([0.0, 90.0], n_zones),
                    window_shgc=0.6,
                    latitude_deg=40.0,
                    max_solar_irradiance=800.0
                )

                # Wrap component as node
                solar_inputs = {
                    "T_outdoor": "T_outdoor",
                    "weather_factor": "weather_factor",
                }
                node = BuildingNode(component, input_map=solar_inputs, name="solar")
        print(name + " created")
        return component, node
    
    def pad_attribute(self, values, n_zones):
        if len(values) > n_zones:
            return values[:n_zones]
        
        return values + [0.0] * (n_zones - len(values))
    
    def pad_matrix(self, values, n_zones):
        # values looks like [[1.0, 0.0], [0.0, 1.0]]
        # new_matrix = [[1.0, 0.0]] if n_zones = 1
        new_matrix = values.copy()

        if len(values) > n_zones:
            new_matrix = values[:n_zones]
            # for every list in new_matrix cut down to n_zone size
            for i in range (len(new_matrix)):
                new_matrix[i] = new_matrix[i][:n_zones]
        
        else:
            # add empty list to account for n_zones to new_matrix
            for i in range(n_zones - len(new_matrix)):
                new_matrix.append([0.0] * n_zones)
            # new_matrix is now [[1.0, 0.0], [0.0, 1.0], [0.0], [0.0]] if n_zones = 4
            for i in range (len(new_matrix)):
                if len(new_matrix[i]) < n_zones:
                    new_matrix[i] = new_matrix[i] + [0.0] * (n_zones - len(new_matrix[i]))
        return new_matrix
                
        
    # -----------------------------
    # Context Menu
    # -----------------------------
    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("Delete")
        property_action = menu.addAction("Update properties")

        selected_action = menu.exec(event.screenPos())

        if selected_action == delete_action:
            self.building_model.remove_componentItem(self)
            self.component = None
            self.node = None
            scene = self.scene()
            if scene:
                scene.removeItem(self)
        elif selected_action == property_action:
            dlg = PropertyDialog(self.component)
            dlg.exec()
