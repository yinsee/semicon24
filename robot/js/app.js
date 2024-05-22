new Vue({
    el: '#app',
    data: {
        sensorStatus: {
            pick_oven: false,
            put_oven: false,
            pick_desiccator: false,
            put_desiccator: false,
            pick_count: 0,
            stop: true,
        },
        brokerAddress: 'ws://192.168.0.42:9001',
        deviceName: 'robot',
        commandTopic: '',
        dataTopic: '',
        chart: null,
        chartData: [],
        chartLabels: [],
    },
    created() {
        this.commandTopic = `/${this.deviceName}/command`;
        this.dataTopic = `/${this.deviceName}/data`;
    },
    mounted() {
        this.initMQTT();
        this.initChart();
    },
    computed: {
        status() {
            if (this.sensorStatus.stop == true) return 'Stopped';
            else if (this.sensorStatus.pick_oven == true) return 'Oven Out';
            else if (this.sensorStatus.put_oven == true) return 'Oven In';
            else if (this.sensorStatus.pick_desiccator == true) return 'Desic Out';
            else if (this.sensorStatus.put_desiccator == true) return 'Desic In';
            return 'Idle';
        }
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
                    this.updateChart(data.pick_count);
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
        initChart() {
            const ctx = document.getElementById('pickCountChart').getContext('2d');
            this.chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: this.chartLabels,
                    datasets: [{
                        label: 'Units Per Hour',
                        data: this.chartData,
                        // borderColor: 'rgba(75, 192, 192, 1)',
                        backgroundColor: 'rgba(75, 192, 192, 1)',
                        fill: true,
                    }],

                },
                options: {
                    responsive: true,
                    aspectRatio: 1.5,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'hour',
                                tooltipFormat: 'MMM D, hA',
                                displayFormats: {
                                    hour: 'hA'
                                }
                            },
                            title: {
                                display: true,
                                text: 'Time'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Pick Count'
                            },
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                    }
                }
            });
        },

        updateChart(pickCount) {
            const now = new Date();
            const hour = now.setMinutes(0, 0, 0);

            this.chartData[hour] = pickCount;

            // Update the chart labels and data
            this.chartLabels = Object.keys(this.chartData).map(ts => new Date(parseInt(ts)));
            this.chart.data.labels = this.chartLabels;
            this.chart.data.datasets[0].data = Object.values(this.chartData);

            // Remove data older than 24 hours
            const cutoff = now.getTime() - 24 * 60 * 60 * 1000;
            this.chartLabels = this.chartLabels.filter(label => label >= cutoff);
            this.chart.data.labels = this.chartLabels;
            this.chart.data.datasets[0].data = this.chartLabels.map(label => this.chartData[label.getTime()]);

            this.chart.update();
        }
    }
});
