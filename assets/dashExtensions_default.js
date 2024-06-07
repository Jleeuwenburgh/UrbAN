window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
            const {
                classes,
                colorscale,
                style,
                colorProp,
                testprop,
                municipality
            } = context.hideout; // get props from hideout
            const value = feature.properties[colorProp]; // get value the determines the color
            for (let i = 0; i < classes.length; ++i) {
                if (value > classes[i]) {
                    style.fillColor = colorscale[i]; // set the fill color according to the class
                }
            }
            return style;
        },
        function1: function(feature, context) {
            const {
                classes,
                colorscale,
                style,
                colorProp,
                testprop,
                municipality
            } = context.hideout; // get props from hideout
            const value = feature.properties[testprop]; // get value the determines the color
            // console.log('value: ', value)
            // console.log('municipality: ', municipality)
            for (let i = 0; i < classes.length; ++i) {
                if (value == municipality) {
                    style.fillColor = 'rgba( 255, 255, 255, 0.0 )'; // set the fill color according to the class
                } else {
                    style.fillColor = 'rgba( 0, 0, 0, 1)'; // set the fill color according to the class
                }
            }
            return style;
        },
        function2: function(feature, context) {
            const {
                classes,
                colorscale,
                style,
                colorProp,
                testprop,
                municipality
            } = context.hideout; // get props from hideout
            const value = feature.properties[testprop]; // get value the determines the color
            // console.log('value: ', value)
            // console.log('municipality: ', municipality)
            for (let i = 0; i < classes.length; ++i) {
                if (value == municipality) {
                    style.color = 'darkgray'; // set the fill color according to the class
                } else {
                    style.color = 'rgba( 255, 255, 255, 0)'; // set the fill color according to the class
                }
            }
            return style;
        }
    }
});