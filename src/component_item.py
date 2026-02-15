from PyQt6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QMenu
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from neuromancer.hvac.building_components import RTU, VAVBox, Envelope, SolarGains


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

        n_zones = 2
        match name:
            case "RTU":
                self.component = RTU(
                    n_zones=n_zones,
                    airflow_max=4.0,      # Total system capacity [kg/s]
                    airflow_oa_min=0.4,      # Minimum outdoor air [kg/s]
                    Q_coil_max=20000.,     # Heating/cooling capacity [W]
                    fan_power_per_flow=800.,  # Fan efficiency [W/(kg/s)]
                    cooling_COP=3.2,      # Cooling efficiency
                    heating_efficiency=0.88  # Heating efficiency
                )
            case "Envelope":
                self.component = Envelope(
                    n_zones=n_zones,
                    R_env=[0.1, 0.12],    # Zone-specific thermal resistance [K/W]
                    C_env=[1.2e6, 1.0e6],  # Zone-specific thermal mass [J/K]
                    R_internal=0.05,      # Inter-zone resistance [K/W]
                    adjacency=[[1.0, 0.0], [0.0, 1.0]],  # Identity matrix, seperate zones
                )
            case "VAVBox":
                self.component = VAVBox(
                    n_zones=n_zones,
                    airflow_min=[0.1, 0.08],     # Zone minimums [kg/s]
                    airflow_max=[0.8, 0.6],      # Zone maximums [kg/s]
                    control_gain=[2.5, 2.0],     # Zone control sensitivity
                    Q_reheat_max=[3000, 2500],  # Zone reheat capacity [W]
                    reheat_efficiency=0.95       # Electric reheat efficiency
                )
            case "SolarGains":
                self.component = SolarGains(
                    n_zones=n_zones,
                    window_area=25.0,
                    window_orientation=[0.0, 90.0],
                    window_shgc=0.6,
                    latitude_deg=40.0,
                    max_solar_irradiance=800.0
                )
        print(name + " created")

    # -----------------------------
    # Context Menu
    # -----------------------------
    def contextMenuEvent(self, event):
        menu = QMenu()
        delete_action = menu.addAction("Delete")

        # ----------------------
        # Property submenu
        # ----------------------
        property_menu = menu.addMenu("Display properties")
        for key, value in vars(self.component).items():
            property_menu.addAction(key)
            print(f"{key}: {value}")

        selected_action = menu.exec(event.screenPos())

        if selected_action == delete_action:
            scene = self.scene()
            if scene:
                scene.removeItem(self)

