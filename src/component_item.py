from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QMenu
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from neuromancer.hvac.building_components import RTU, VAVBox, Envelope, SolarGains
from neuromancer.hvac.building import BuildingNode
from property_dialog import PropertyDialog


class ComponentItem(QGraphicsRectItem):
    """Rectangle + text representing a building component"""

    def __init__(self, name, pos):
        super().__init__(0, 0, 120, 50)

        self.setPos(pos)
        self.setBrush(QColor(100, 200, 250, 180))

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
        )

        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        self.label.setPos(10, 10)
        self.component, self.node = self.createComponent(name)

    def createComponent(self, name):

        n_zones = 2
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
                    R_env=[0.1, 0.12],    # Zone-specific thermal resistance [K/W]
                    C_env=[1.2e6, 1.0e6],  # Zone-specific thermal mass [J/K]
                    R_internal=0.05,      # Inter-zone resistance [K/W]
                    adjacency=[[1.0, 0.0], [0.0, 1.0]],  # Identity matrix, seperate zones
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
                    airflow_min=[0.1, 0.08],     # Zone minimums [kg/s]
                    airflow_max=[0.8, 0.6],      # Zone maximums [kg/s]
                    control_gain=[2.5, 2.0],     # Zone control sensitivity
                    Q_reheat_max=[3000, 2500],  # Zone reheat capacity [W]
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
                    window_orientation=[0.0, 90.0],
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
                # component = SolarGains(
                #     n_zones=n_zones,
                #     window_area=25.0,
                #     window_orientation=[0.0, 90.0],
                #     window_shgc=0.6,
                #     latitude_deg=40.0,
                #     max_solar_irradiance=800.0
                # )
    # -----------------------------
    # Context Menu
    # -----------------------------
    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("Delete")

        # ----------------------
        # Property submenu
        # ----------------------
        property_action = menu.addAction("Display properties")

        selected_action = menu.exec(event.screenPos())

        if selected_action == delete_action:
            scene = self.scene()
            if scene:
                scene.removeItem(self)
        elif selected_action == property_action:
            dlg = PropertyDialog(self.component)
            dlg.exec()
