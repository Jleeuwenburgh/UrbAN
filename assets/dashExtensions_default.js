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
            } = context.hideout; // get props
            const csc = chroma.scale('YlGn').gamma(2).domain([0, 4]);
            style.color = csc(feature.properties[colorProp]); // set the fill color according to the class
            style.fillColor = csc(feature.properties[colorProp]); // set the fill color according to the class
            style.color = 'black';
            style.fillOpacity = 1;
            style.weight = 0.5;
            //const value = feature.properties[colorProp];  // get value the determines the color
            //for (let i = 0; i < classes.length; ++i) {
            //    if (value > classes[i]) {
            //        style.fillColor = colorscale[i];  // set the fill color according to the class
            //    }
            //}
            return style;
        },
        function1: function(feature, context) {
            const {
                classes,
                colorscale,
                style,
                colorProp,
                testprop,
                municipality,
                vmin,
                vmax
            } = context.hideout;
            const value = feature.properties[colorProp]; // get value the determines the color
            for (let i = 0; i < classes.length; ++i) {
                if (value > classes[i]) {
                    style.fillColor = colorscale[i]; // set the fill color according to the class
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
            } = context.hideout;
            const value = feature.properties[testprop]; // get value the determines the color
            // console.log('value: ', value)
            // console.log('municipality: ', municipality)
            for (let i = 0; i < classes.length; ++i) {
                if (value == municipality) {
                    style.fillColor = 'rgba( 255, 255, 255, 0.0 )'; // set the fill color according to the class
                } else {
                    style.fillColor = 'rgba( 0, 0, 0, 0.8)'; // set the fill color according to the class
                }
            }
            return style;
        },
        function3: function(feature, context) {
            const {
                classes,
                colorscale,
                style,
                colorProp,
                testprop,
                municipality,
                vmin,
                vmax
            } = context.hideout;
            const value = feature.properties[testprop]; // get value the determines the color
            // console.log('value: ', value)
            // console.log('municipality: ', municipality)
            const csc = chroma.scale('YlGn').gamma(2).domain([0, vmax]); // chroma lib to construct colorscale

            for (let i = 0; i < classes.length; ++i) {
                if (value == municipality) {
                    style.color = 'darkgray'; // set the fill color according to the class
                    style.fillColor = csc(feature.properties[colorProp]);
                    style.fillOpacity = 0.7;
                    style.weight = 1;
                } else {
                    style.color = 'rgba( 255, 255, 255, 0)'; // set the fill color according to the class
                    style.fillColor = 'white'; // set the fill color according to the class
                    style.fillOpacity = 0;
                    style.weight = 0;
                }
            }
            return style;
        },
        function4: function(feature, context) {
            const {
                colorscale,
                classes,
                style,
                colorProp,
                testprop,
                municipality,
                vmin,
                vmax
            } = context.hideout;
            const csc = chroma.scale('YlGn').gamma(2).domain([0, vmax]); // chroma lib to construct colorscale
            style.color = csc(feature.properties[colorProp]); // set the fill color according to the class
            style.fillColor = csc(feature.properties[colorProp]); // set the fill color according to the class
            style.color = 'darkgrey';
            style.fillOpacity = 0.8;
            style.weight = 0.3;
            return style;
        }
    }
});