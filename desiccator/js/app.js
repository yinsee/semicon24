TEMPERATURE_THRESHOLD = 40;
HUMIDITY_THRESHOLD = 50;
HUMIDITY_ALARM_THRESHOLD = 70;

new Vue({
    el: '#app',
    data: {
        sensorStatus: {
            limit_switches: [false, false, false, false],
            door_close: false,
            door_open: false,
            safety_curtain: true,
            temperature: 0,
            humidity: 0,
            alarm: 0,
            gas: 0
        },
        temperatureData: [],
        humidityData: [],
        temperatureChart: null,
        humidityChart: null,
        brokerAddress: 'ws://192.168.0.42:9001',
        deviceName: 'desiccator',
        commandTopic: '',
        dataTopic: '',
        TEMPERATURE_THRESHOLD,
        HUMIDITY_THRESHOLD,
        HUMIDITY_ALARM_THRESHOLD,
    },
    created() {
        this.commandTopic = `/${this.deviceName}/command`;
        this.dataTopic = `/${this.deviceName}/data`;
    },
    mounted() {
        this.initMQTT();
        this.initCharts();
    },
    computed: {
        unitsCount() {
            return this.sensorStatus.limit_switches.filter(status => status).length;
        },
        status() {
            if (this.sensorStatus.cylinder_top == true) {
                return 'Closed';
            } else {
                return 'Open';
            }
        },
    },
    methods: {
        initMQTT() {
            const client = mqtt.connect(this.brokerAddress);

            client.on('connect', () => {
                console.log('Connected to MQTT broker');
                console.log(this.dataTopic);
                client.subscribe(this.dataTopic);
            });

            client.on('message', (topic, message) => {
                if (topic === this.dataTopic) {
                    const data = JSON.parse(message.toString());
                    console.log(data);
                    this.updateStatus(data);
                    this.updateCharts(data);
                }
            });

            this.client = client;
        },
        sendCommand(command) {
            console.log(this.commandTopic, command);
            this.client.publish(this.commandTopic, command);
        },
        updateStatus(data) {
            this.sensorStatus = data;
        },
        initCharts() {
            const temperatureCtx = document.getElementById('temperatureChart').getContext('2d');
            const humidityCtx = document.getElementById('humidityChart').getContext('2d');

            const drawThresholdLines = (chart, values, colors) => {
                const ctx = chart.ctx;
                const yScale = chart.scales['y'];
                const xScale = chart.scales['x'];

                values.forEach((value, index) => {
                    ctx.save();
                    ctx.beginPath();
                    ctx.strokeStyle = colors[index];
                    ctx.lineWidth = 0.5;
                    ctx.moveTo(xScale.left, yScale.getPixelForValue(value));
                    ctx.lineTo(xScale.right, yScale.getPixelForValue(value));
                    ctx.stroke();
                    ctx.restore();
                });

            };

            this.temperatureChart = new Chart(temperatureCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Temperature (°C)',
                        data: [],
                        borderColor: 'lime',
                        fill: false
                    }]
                },
                options: {
                    aspectRatio: 1.75,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'minute'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            max: 50
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        annotation: {
                            drawTime: 'afterDatasetsDraw',
                            annotations: {
                                drawThresholdLines
                            }
                        }
                    }
                },
                plugins: [{
                    id: 'thresholdLines',
                    beforeDraw: (chart) => drawThresholdLines(chart, [TEMPERATURE_THRESHOLD], ['red'])
                }]
            });

            this.humidityChart = new Chart(humidityCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Humidity (%)',
                        data: [],
                        borderColor: 'cyan',
                        fill: false
                    }]
                },
                options: {
                    aspectRatio: 1.75,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'minute'
                            }
                        },
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        annotation: {
                            drawTime: 'afterDatasetsDraw',
                            annotations: {
                                drawThresholdLines
                            }
                        }
                    }
                },
                plugins: [{
                    id: 'thresholdLines',
                    beforeDraw: (chart) => drawThresholdLines(chart, [HUMIDITY_THRESHOLD, HUMIDITY_ALARM_THRESHOLD], ['yellow', 'red'])
                }]

            });
        },
        updateCharts(data) {
            const now = new Date();
            const minuteTimestamp = new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours(), now.getMinutes());

            if (!this.lastTempUpdate || minuteTimestamp > this.lastTempUpdate) {
                this.temperatureChart.data.labels.push(minuteTimestamp);
                this.temperatureChart.data.datasets[0].data.push(data.temperature);
                this.lastTempUpdate = minuteTimestamp;

                if (this.temperatureChart.data.labels.length > 1440) {
                    this.temperatureChart.data.labels.shift();
                    this.temperatureChart.data.datasets[0].data.shift();
                }
            } else {
                this.temperatureChart.data.datasets[0].data[this.temperatureChart.data.datasets[0].data.length - 1] = data.temperature;
            }

            if (!this.lastHumidityUpdate || minuteTimestamp > this.lastHumidityUpdate) {
                this.humidityChart.data.labels.push(minuteTimestamp);
                this.humidityChart.data.datasets[0].data.push(data.humidity);
                this.lastHumidityUpdate = minuteTimestamp;

                if (this.humidityChart.data.labels.length > 1440) {
                    this.humidityChart.data.labels.shift();
                    this.humidityChart.data.datasets[0].data.shift();
                }
            } else {
                this.humidityChart.data.datasets[0].data[this.humidityChart.data.datasets[0].data.length - 1] = data.humidity;
            }

            this.temperatureChart.update();
            this.humidityChart.update();
        }
    }
});
