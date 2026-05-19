
#include <stdint.h>
#include <stdio.h>

// Device Header
#include <ti/devices/msp432e4/inc/msp432e401y.h>

/* DriverLib Includes */
#include <ti/devices/msp432e4/driverlib/driverlib.h>

//macro
#define LDC1101_CHIP_ID             0x3F
#define LDC1101_START_CONFIG        0x0B
#define LDC1101_RP_SET              0x01
#define LDC1101_DIG_CONFIG          0x04
#define LDC1101_ALT_CONFIG          0x05
#define LDC1101_D_CONF              0x0C
#define LDC1101_LHR_RCOUNT_LSB      0x30
#define LDC1101_LHR_RCOUNT_MSB      0x31
#define LDC1101_STATUS              0x20

//function prototypes
void System_clock_init(void);
void Gpio_Init(void);
void SPI_Init(void);
void UART_Init(void);
void PWM_Init_16MHz(void);
void Delay_ms(uint32_t ms);
uint8_t LDC_ReadReg(uint8_t reg);
uint8_t SPI_Transfer(uint8_t data);
void  LMode(void);
void LDC_WriteReg(uint8_t reg, uint8_t val);
uint8_t LDC_READ_STATUS(void);
void UART_WriteString(char *str);
uint32_t Read_LHR_Data(void);
void UART_Write_Hex(uint8_t chipId);
void UART_WriteByte(uint8_t data);
void Debug_LHR_Registers(void);
void UART_Write_Hex32(uint32_t value);
void UART_Write_Dec(uint32_t value);
void UART_Write_Digit(uint8_t digit);
void Convert_LHR_to_Distance(uint32_t lhr, double *freq, double *inductance, double *distance);
double LHR_to_Frequency(uint32_t lhr_value);
double Frequency_to_Inductance(double f_sensor);
double Inductance_to_Distance(double L_sensor);
void UART_ProcessByte(uint8_t byte);

//Global variables
uint32_t system_clk;
volatile uint8_t chipId;
volatile uint8_t status;
volatile uint32_t LHR_VAL;
volatile uint8_t lsb, mid, msb;
double frequency, inductance, distance;
volatile uint32_t freq_M;
volatile uint32_t L_u;
volatile uint32_t dist_mm;
volatile double C_sensor = 390e-12;  // Updated via UART from GUI


//pin definitions
#define SPI_CLK_PORT     GPIO_PORTD_BASE
#define SPI_CLK_PIN      GPIO_PIN_3
#define SPI_MISO_PORT    GPIO_PORTD_BASE
#define SPI_MISO_PIN     GPIO_PIN_0
#define SPI_MOSI_PORT    GPIO_PORTD_BASE
#define SPI_MOSI_PIN     GPIO_PIN_1
#define SPI_CS_PORT      GPIO_PORTB_BASE
#define SPI_CS_PIN       GPIO_PIN_5
#define PWM_PORT         GPIO_PORTF_BASE
#define PWM_PIN          GPIO_PIN_1
//#define UART_Tx
//#define UART_Rx

#define CMD_BUF_SIZE 32
char cmd_buf[CMD_BUF_SIZE];
uint8_t cmd_idx = 0;

void UART_ProcessByte(uint8_t byte) {
    if (byte == '\n' || byte == '\r') {
        if (cmd_idx > 0) {
            cmd_buf[cmd_idx] = '\0';
            if (cmd_buf[0]=='C' && cmd_buf[1]=='S' && cmd_buf[2]=='E' &&
                cmd_buf[3]=='N' && cmd_buf[4]=='S' && cmd_buf[5]=='O' &&
                cmd_buf[6]=='R' && cmd_buf[7]==':') {
                double pf = 0.0;
                int i = 8;
                while (cmd_buf[i] >= '0' && cmd_buf[i] <= '9') {
                    pf = pf * 10.0 + (cmd_buf[i] - '0');
                    i++;
                }
                if (pf > 0.0) {
                    C_sensor = pf * 1e-12;
                    UART_WriteString("CSENSOR_ACK:");
                    UART_Write_Dec((uint32_t)pf);   // Echo back the pF value
                    UART_WriteString("pF\r\n");
                }
            }
            
            cmd_idx = 0;
        }
    } else if (cmd_idx < CMD_BUF_SIZE - 1) {
        cmd_buf[cmd_idx++] = (char)byte;
    }
}

int main(void)
{
    //basic cpu setup
    SystemInit();
    System_clock_init();
    UART_Init();
    //configure the clock hardware


    SPI_Init();
    Delay_ms(10);
    //GPIO_INIT
    Gpio_Init();

   // SPI_Init();

    //pwm
    PWM_Init_16MHz();


    //delay
    Delay_ms(100);

    chipId = LDC_ReadReg(LDC1101_CHIP_ID);
    //printf("%d", chipId );
    //configure LMODE
    LMode();
    status = LDC_READ_STATUS();

    UART_WriteString("Chip ID: 0x");
    UART_Write_Hex(chipId);
    UART_WriteString("\r\n");


    UART_WriteString("Status: 0x");
    UART_Write_Hex(status);
    UART_WriteString("\r\n");

    if(status & 0x80)
    {
        // Sensor not oscillating
        UART_WriteString("ERROR: NO_SENSOR_OSC\r\n");
        while(1);//stop

    }
    UART_WriteString("SUCCESS: LDC1101 ready!\r\n");
    Delay_ms(1000);
    //char buffer[100];
    while(1)
    {
        // Poll for incoming UART commands (non-blocking)
        while (!(UART0->FR & UART_FR_RXFE)) {
            uint8_t rx_byte = (uint8_t)(UART0->DR & 0xFF);
            UART_ProcessByte(rx_byte);
        }

        GPIOPinWrite(GPIO_PORTB_BASE, GPIO_PIN_5, 0);          // CS LOW
        SSIDataPut(SSI2_BASE, 0xAA);                            // Send "dummy" 0xAA
        while(SSIBusy(SSI2_BASE));                             // Wait
        GPIOPinWrite(GPIO_PORTB_BASE, GPIO_PIN_5, GPIO_PIN_5); // CS HIGH
        //read status
        status = LDC_READ_STATUS();
        //error check
        if(status & 0x80)
        {
            UART_WriteString("ERROR: Oscillation stopped!\r\n");
            Delay_ms(100);
            continue;
        }
        //read lhr
        LHR_VAL = Read_LHR_Data();
        Debug_LHR_Registers();

        Convert_LHR_to_Distance(LHR_VAL, &frequency, &inductance, &distance);

        UART_WriteString("LHR VALUE: 0x");
        UART_Write_Hex32(LHR_VAL);
        UART_WriteString("\r\n");

        Delay_ms(100);

        //freq
        freq_M = frequency / 1000000;
        UART_Write_Dec(freq_M);
        UART_WriteString(" MHz");

        //inductance
        L_u = (inductance * 1e6 * 100);  // 2 decimal places
        UART_Write_Dec(L_u / 100);
        UART_WriteString(".");
        UART_Write_Dec(L_u % 100);
        UART_WriteString(" uH");

        //distance
        dist_mm = distance * 100;  // 2 decimal places
        UART_Write_Dec(dist_mm / 100);
        UART_WriteString(".");
        UART_Write_Dec(dist_mm % 100);
        UART_WriteString(" mm");
        UART_WriteString("\r\n");

        // After existing UART output lines, add:
        UART_WriteString("CSENSOR_VAL:");
        UART_Write_Dec((uint32_t)(C_sensor * 1e12));  // Send as pF integer
        UART_WriteString("pF\r\n");

        Delay_ms(100);
    }
}

void System_clock_init(void)
{

    //driver level, 48MHz
    system_clk = SysCtlClockFreqSet (SYSCTL_OSC_INT | SYSCTL_USE_PLL | SYSCTL_CFG_VCO_480,   48000000);
}

void Gpio_Init(void)
{

    //driver lib
    //enable clk
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOB);
    //wait
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOB));
    //pb5 as output
    GPIOPinTypeGPIOOutput(GPIO_PORTB_BASE, GPIO_PIN_5);
    //set high
    GPIOPinWrite(GPIO_PORTB_BASE, GPIO_PIN_5, GPIO_PIN_5);
}

void SPI_Init(void)
{
    //driver level
    //1. enable ssi and gpio
    SysCtlPeripheralEnable(SYSCTL_PERIPH_SSI2);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOD);
    //wiat until ready
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_SSI2));
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOD));
    //configure pinsfor ssi1
    //miso
    GPIOPinConfigure(GPIO_PD0_SSI2XDAT1);
    //mosi
    GPIOPinConfigure(GPIO_PD1_SSI2XDAT0);
    //sclk
    GPIOPinConfigure(GPIO_PD3_SSI2CLK);

    //gpio handled by ssi peri
    GPIOPinTypeSSI(GPIO_PORTD_BASE, GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_3);
    //configure
    SSIConfigSetExpClk(SSI2_BASE, system_clk,
                       SSI_FRF_MOTO_MODE_0, SSI_MODE_MASTER,
                       100000, 8);
    SSIEnable(SSI2_BASE);

}

void PWM_Init_16MHz(void)
{

    SysCtlPeripheralEnable(SYSCTL_PERIPH_PWM0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOF);

    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_PWM0));
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOF));


    //configure pf1 as pwm1
    GPIOPinConfigure(GPIO_PF1_M0PWM1);
    GPIOPinTypePWM(GPIO_PORTF_BASE, GPIO_PIN_1);

    PWMClockSet(PWM0_BASE, PWM_SYSCLK_DIV_1);

    //Disable generator during setup
    PWMGenDisable(PWM0_BASE, PWM_GEN_0);

    //configure pwm generator 0
    PWMGenConfigure(PWM0_BASE, PWM_GEN_0, PWM_GEN_MODE_DOWN | PWM_GEN_MODE_NO_SYNC);

    //set period, 16M from 48M
    //PWMGenPeriodSet(PWM0_BASE, PWM_GEN_0, 3);
    PWMGenPeriodSet(PWM0_BASE, PWM_GEN_0, 3);
    //50% duty cycle
    PWMPulseWidthSet(PWM0_BASE, PWM_OUT_1, 1);

    //eable generator
    PWMGenEnable(PWM0_BASE, PWM_GEN_0);

    //enable the output
    PWMOutputState(PWM0_BASE, PWM_OUT_1_BIT, true);


}

void UART_Init(void)
{
    SysCtlPeripheralEnable(SYSCTL_PERIPH_UART0);
    SysCtlPeripheralEnable(SYSCTL_PERIPH_GPIOA);

    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_UART0));
    while(!SysCtlPeripheralReady(SYSCTL_PERIPH_GPIOA));

    GPIOPinConfigure(GPIO_PA0_U0RX);
    GPIOPinConfigure(GPIO_PA1_U0TX);

    GPIOPinTypeUART(GPIO_PORTA_BASE, GPIO_PIN_0 | GPIO_PIN_1);
    //configuring the uart
    UARTConfigSetExpClk(UART0_BASE, system_clk, 115200, UART_CONFIG_WLEN_8 | UART_CONFIG_STOP_ONE | UART_CONFIG_PAR_NONE);
    UARTEnable(UART0_BASE);

}

void Delay_ms(uint32_t ms)
{
    //SysCtlDelay((system_clk / 3000) * ms);
    volatile uint32_t i;
    for( i = 0; i < ms * 12000; i++);
}

uint8_t LDC_ReadReg(uint8_t reg)
{
    uint8_t value;
    //cs low
    GPIOPinWrite(GPIO_PORTB_BASE ,GPIO_PIN_5  ,  0);
   // SysCtlDelay(system_clk / 300000);
    volatile uint32_t i;
    for(i = 0; i < 100; i++);
    //send the read command
    SPI_Transfer(0x80 | (reg & 0x7F));
    //dummy write to recive data
    value = SPI_Transfer(0x00);
    GPIOPinWrite(GPIO_PORTB_BASE ,GPIO_PIN_5  , GPIO_PIN_5);
    //SysCtlDelay(system_clk / 1000000);
    //volatile uint32_t i;
    for( i = 0; i < 20; i++);
    return value;
}



uint8_t SPI_Transfer(uint8_t data)
{
    uint32_t rx;
    // 1. Clear out any junk in the RX FIFO before sending
        while(SSIDataGetNonBlocking(SSI2_BASE, &rx));
    //send data
    SSIDataPut(SSI2_BASE, data);
    //wait
   while(SSIBusy(SSI2_BASE));
   // while(!SSI2->SR & SSI_SR_RNE)
    //read rx data
    SSIDataGet(SSI2_BASE, &rx);
    return (uint8_t)rx;
}

void  LMode(void)
{
    //sleep mode, start config = sleep
    LDC_WriteReg(LDC1101_START_CONFIG, 0x01);
    Delay_ms(10);

    LDC_WriteReg(LDC1101_RP_SET , 0x74);
    LDC_WriteReg(LDC1101_DIG_CONFIG, 0xC7);//4Mhz
    LDC_WriteReg(LDC1101_ALT_CONFIG, 0x01);//l only
    LDC_WriteReg(LDC1101_D_CONF, 0x01);
    LDC_WriteReg(LDC1101_LHR_RCOUNT_LSB, 0xE8);
    LDC_WriteReg(LDC1101_LHR_RCOUNT_MSB, 0x03);

    //exit sleep mode, start config = Active (start conversation)
    LDC_WriteReg(LDC1101_START_CONFIG, 0x00);
    Delay_ms(10);

    //configure reg

}

void LDC_WriteReg(uint8_t reg, uint8_t val)
{
    //cs low
    GPIOPinWrite(SPI_CS_PORT, SPI_CS_PIN, 0);
    //send reg adress
    SPI_Transfer(reg & 0x7F);
    //send data
    SPI_Transfer(val);
    //cs high
    GPIOPinWrite(SPI_CS_PORT, SPI_CS_PIN, SPI_CS_PIN);

}

uint8_t LDC_READ_STATUS(void)
{
    return LDC_ReadReg(LDC1101_STATUS);
}

void UART_WriteString(char *str)
{
    while(*str)
    {
        while(UART0->FR & UART_FR_TXFF);
        UART0->DR = *str++;
//        while(UARTBusy(UART0_BASE));
//        UARTCharPut(UART0_BASE, *str++);
    }
}

uint32_t Read_LHR_Data(void)
{


    GPIOPinWrite(SPI_CS_PORT, SPI_CS_PIN, 0);
    //SysCtlDelay(system_clk / 300000);
    volatile uint32_t i;
    for( i = 0; i < 100; i++);

    SPI_Transfer(0x80 | 0x38);  // Address of LHR_DATA_LSB, read mode
    lsb = SPI_Transfer(0x00);   // Auto-increments to 0x39
    mid = SPI_Transfer(0x00);   // Auto-increments to 0x3A
    msb = SPI_Transfer(0x00);

    GPIOPinWrite(SPI_CS_PORT, SPI_CS_PIN, SPI_CS_PIN);

    return ((uint32_t)msb << 16) | ((uint32_t)mid << 8) | lsb;
}

void Debug_LHR_Registers(void) {
    uint8_t lsb = LDC_ReadReg(0x38);
    uint8_t mid = LDC_ReadReg(0x39);
    uint8_t msb = LDC_ReadReg(0x3A);

    UART_WriteString("LHR_LSB (0x38): 0x");
    UART_Write_Hex(lsb);
    UART_WriteString("\r\n");

    UART_WriteString("LHR_MID (0x39): 0x");
    UART_Write_Hex(mid);
    UART_WriteString("\r\n");

    UART_WriteString("LHR_MSB (0x3A): 0x");
    UART_Write_Hex(msb);
    UART_WriteString("\r\n");

    uint32_t combined = ((uint32_t)msb << 16) | ((uint32_t)mid << 8) | lsb;
    UART_WriteString("Combined: 0x");
    UART_Write_Hex32(combined);
    UART_WriteString("\r\n");
}

void UART_Write_Hex(uint8_t value)
{
    const char hex_chars[] = "0123456789ABCDEF";
    UART_WriteByte(hex_chars[(value >> 4) & 0x0F]);
    UART_WriteByte(hex_chars[value & 0x0F]);
}

void UART_WriteByte(uint8_t data) {
    while(UART0->FR & UART_FR_TXFF);
    UART0->DR = data;
}

void UART_Write_Hex32(uint32_t value) {
    const char hex_chars[] = "0123456789ABCDEF";
    int i = 0;
    for( i = 7; i >= 0; i--) {
        UART_WriteByte(hex_chars[(value >> (i * 4)) & 0x0F]);
    }
}

void UART_Write_Dec(uint32_t value) {
    // Handle zero case
    if(value == 0) {
        UART_WriteByte('0');
        return;
    }

    // Extract digits (reverse order)
    uint8_t digits[12];  // Max 10 digits for 32-bit + null
    uint8_t i = 0;

    while(value > 0) {
        digits[i++] = value % 10;  // Get last digit
        value /= 10;                // Remove last digit
    }

    // Print digits in correct order (reverse)
    while(i > 0) {
        UART_Write_Digit(digits[--i]);
    }
}

void UART_Write_Digit(uint8_t digit)
{
    if(digit < 10)
    {
        UART_WriteByte(digit + '0');  // Convert 0-9 to '0'-'9'
    }
}

void Convert_LHR_to_Distance(uint32_t lhr, double *freq, double *inductance, double *distance)
{
    *freq = LHR_to_Frequency(lhr);
    *inductance = Frequency_to_Inductance(*freq);
    *distance = Inductance_to_Distance(*inductance);
}

double LHR_to_Frequency(uint32_t lhr_value) {
    double f_sensor;

    // f_sensor = (f_CLKIN × LHR_DATA) / 2^24
    f_sensor = (16000000.0 * (double)lhr_value) / 16777216.0;

    return f_sensor;  // In Hz
}

double Frequency_to_Inductance(double f_sensor) {
    double L_sensor;

    // L = 1 / ((2πf)² × C)
    L_sensor = 1.0 / (4.0 * 3.14159265359 * 3.14159265359 *
                       f_sensor * f_sensor * C_sensor);

    return L_sensor;  // In Henrys
}

double Inductance_to_Distance(double L_sensor) {
    double distance_mm;

    // calibrate with known distances
    // Example: distance = a × L + b

    // Temporary formula (replace after calibration):
    distance_mm = (L_sensor * 1e6 - 5.0) * 10.0;  // Fake

    return distance_mm;  // In millimeters
}
