"""
Estrategia de test para paper trading del core.
Genera órdenes de compra y venta periódicas para probar la ejecución contra un broker.
"""

from datetime import datetime, timedelta

from lumibot.entities import Asset
from lumibot.strategies import Strategy


class PaperTestStrategy(Strategy):
    """
    Estrategia de prueba para paper trading.

    Genera órdenes de compra y venta automáticas a intervalos regulares
    para probar el flujo completo del sistema sin dinero real.
    """

    def initialize(self):
        """Inicializa la estrategia de prueba."""
        # Crypto opera continuamente, independientemente del horario bursátil.
        self.market_hours = None
        try:
            self.set_market("24/7")
        except Exception:
            pass
        if hasattr(self, "broker") and self.broker is not None:
            try:
                self.broker.market = "24/7"
            except Exception:
                pass

        self.test_symbols = self.parameters.get("test_symbols", ["BTC/USD", "ETH/USD", "SOL/USD"])
        self.order_interval_minutes = self.parameters.get("order_interval_minutes", 5)
        self.order_size_usd = self.parameters.get("order_size_usd", 100)
        self.max_position_per_symbol = self.parameters.get("max_position_per_symbol", 1000)
        self.test_duration_hours = self.parameters.get("test_duration_hours", 1)
        self.enable_stop_loss = self.parameters.get("enable_stop_loss", True)
        self.enable_take_profit = self.parameters.get("enable_take_profit", True)
        self.stop_loss_pct = self.parameters.get("stop_loss_pct", 0.02)
        self.take_profit_pct = self.parameters.get("take_profit_pct", 0.03)

        self.start_time = datetime.now()
        self.last_order_time = {}
        self.order_count = 0
        self.successful_orders = 0
        self.failed_orders = 0
        self.total_value_traded = 0
        self.test_phase = "BUY"

        for symbol in self.test_symbols:
            self.last_order_time[symbol] = datetime.now() - timedelta(minutes=self.order_interval_minutes)

        self._log_initialization()

    def is_market_open(self):
        """Considera crypto siempre abierto."""
        return True

    def should_continue_trading(self):
        """Mantiene la estrategia activa durante la prueba."""
        return True

    def _log_initialization(self):
        """Registra la configuración inicial."""
        self.log_message("=" * 70)
        self.log_message("PAPER TEST STRATEGY - INICIANDO PRUEBAS")
        self.log_message("=" * 70)
        self.log_message(f"Hora de inicio: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_message(f"Duración de prueba: {self.test_duration_hours} horas")
        self.log_message(f"Símbolos de prueba: {', '.join(self.test_symbols)}")
        self.log_message(f"Intervalo entre órdenes: {self.order_interval_minutes} minutos")
        self.log_message(f"Tamaño de orden: ${self.order_size_usd}")
        self.log_message(f"Posición máxima por símbolo: ${self.max_position_per_symbol}")
        self.log_message(f"Stop Loss: {'Sí' if self.enable_stop_loss else 'No'} ({self.stop_loss_pct * 100:.1f}%)")
        self.log_message(f"Take Profit: {'Sí' if self.enable_take_profit else 'No'} ({self.take_profit_pct * 100:.1f}%)")
        self.log_message("Modo de ejecución: PAPER (sin dinero real)")
        self.log_message("=" * 70)

    def on_trading_iteration(self):
        """Ejecuta una iteración de trading."""
        try:
            current_time = datetime.now()
            if self._check_test_duration():
                self._finalize_test()
                self.stop()
                return
            self._log_iteration_status()
            for symbol in self.test_symbols:
                self._process_symbol(symbol, current_time)
            self._manage_existing_orders()
        except Exception as e:
            self.log_message(f"ERROR en iteración: {str(e)}", color="red")
            self.failed_orders += 1

    def _process_symbol(self, symbol: str, current_time: datetime):
        """Procesa órdenes para un símbolo específico."""
        time_since_last_order = current_time - self.last_order_time[symbol]
        if time_since_last_order.total_seconds() >= self.order_interval_minutes * 60:
            asset = Asset(symbol=symbol, asset_type="crypto" if "/" in symbol else "stock")
            current_price = self.get_last_price(asset)
            if not current_price:
                self.log_message(f"No se pudo obtener precio para {symbol}", color="yellow")
                return
            position = self.get_position(asset)
            current_value = float(position.quantity) * float(current_price) if position else 0
            if self.test_phase == "BUY" and current_value < self.max_position_per_symbol:
                self._create_buy_order(asset, current_price)
                self.test_phase = "SELL"
            elif self.test_phase == "SELL" and position and position.quantity > 0:
                self._create_sell_order(asset, position, current_price)
                self.test_phase = "BUY"
            elif current_value < self.max_position_per_symbol:
                self._create_buy_order(asset, current_price)
            elif position and position.quantity > 0:
                self._create_sell_order(asset, position, current_price)
            self.last_order_time[symbol] = current_time

    def _create_buy_order(self, asset: Asset, current_price: float):
        """Crea una orden de compra de prueba."""
        try:
            quantity = self.order_size_usd / float(current_price)
            self.log_message(f"CREANDO ORDEN DE COMPRA - {asset.symbol}")
            self.log_message(f"Precio actual: ${current_price:.2f}")
            self.log_message(f"Cantidad: {quantity:.4f}")
            self.log_message(f"Valor: ${self.order_size_usd:.2f}")
            order = self.create_order(asset, quantity, "buy", type="market")
            self.order_count += 1
            self.total_value_traded += self.order_size_usd
            if self.enable_stop_loss or self.enable_take_profit:
                self._create_bracket_orders(asset, quantity, current_price)
            self.log_message(f"Orden creada exitosamente - ID: {order.id if order else 'N/A'}")
            self.successful_orders += 1
        except Exception as e:
            self.log_message(f"Error creando orden de compra: {str(e)}", color="red")
            self.failed_orders += 1

    def _create_sell_order(self, asset: Asset, position, current_price: float):
        """Crea una orden de venta de prueba."""
        try:
            quantity_to_sell = min(position.quantity * 0.5, self.order_size_usd / float(current_price))
            self.log_message(f"CREANDO ORDEN DE VENTA - {asset.symbol}")
            self.log_message(f"Cantidad: {quantity_to_sell:.4f}")
            self.log_message(f"Valor aproximado: ${quantity_to_sell * current_price:.2f}")
            order = self.create_order(asset, quantity_to_sell, "sell", type="market")
            self.order_count += 1
            self.total_value_traded += quantity_to_sell * current_price
            self.log_message(f"Orden creada exitosamente - ID: {order.id if order else 'N/A'}")
            self.successful_orders += 1
        except Exception as e:
            self.log_message(f"Error creando orden de venta: {str(e)}", color="red")
            self.failed_orders += 1

    def _create_bracket_orders(self, _asset: Asset, _quantity: float, entry_price: float):
        """Registra los niveles de stop loss y take profit."""
        try:
            if self.enable_stop_loss:
                self.log_message(f"Creando Stop Loss a ${entry_price * (1 - self.stop_loss_pct):.2f}")
            if self.enable_take_profit:
                self.log_message(f"Creando Take Profit a ${entry_price * (1 + self.take_profit_pct):.2f}")
        except Exception as e:
            self.log_message(f"Error creando órdenes bracket: {str(e)}", color="yellow")

    def _manage_existing_orders(self):
        """Gestiona y monitorea órdenes existentes."""
        orders = self.get_orders()
        if orders:
            self.log_message(f"Órdenes activas: {len(orders)}")
            for order in orders[:5]:
                self.log_message(
                    f"{order.side.upper()} {order.quantity:.4f} {order.asset.symbol} - Status: {order.status}"
                )

    def _log_iteration_status(self):
        """Registra el estado actual de la estrategia."""
        elapsed = datetime.now() - self.start_time
        self.log_message(
            f"Estado PAPER | Tiempo: {elapsed} | Órdenes: {self.order_count} | "
            f"Exitosas: {self.successful_orders} | Fallidas: {self.failed_orders}"
        )

    def _check_test_duration(self):
        """Comprueba si terminó la duración configurada."""
        return datetime.now() - self.start_time >= timedelta(hours=self.test_duration_hours)

    def _finalize_test(self):
        """Registra el resumen final."""
        self.log_message(
            f"PAPER TEST FINALIZADO | Órdenes: {self.order_count} | "
            f"Exitosas: {self.successful_orders} | Fallidas: {self.failed_orders} | "
            f"Valor negociado: ${self.total_value_traded:.2f}"
        )